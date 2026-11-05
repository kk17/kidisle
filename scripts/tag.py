#!/usr/bin/env python3
"""kidisle LLM 过滤打标管线（stage 3）。

读入 data/candidates.json（collect.py 产出），用 OpenAI 兼容接口对每条候选做：
1. 儿童适宜性过滤（kida_safe=false 的直接淘汰）
2. 三维打标：年龄段 / 语言 / 主题（枚举见 src/data/taxonomy.json）

产出 data/tagged.json，再由 build_data.py 汇入 src/data/videos.json 发布。

配置（环境变量）：
    LLM_BASE_URL  默认 https://open.bigmodel.cn/api/paas/v4 （智谱 GLM）
    LLM_API_KEY   必填
    LLM_MODEL     默认 glm-4-flash

用法：
    python3 scripts/tag.py                # 全量，支持断点续跑
    python3 scripts/tag.py --dry-run      # 只打前 3 批试跑
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = json.loads((ROOT / "src/data/taxonomy.json").read_text(encoding="utf-8"))

AGE_IDS = [t["id"] for t in TAXONOMY["age_bands"]]
LANG_IDS = [t["id"] for t in TAXONOMY["languages"]]
THEME_IDS = [t["id"] for t in TAXONOMY["themes"]]

PROMPT_TEMPLATE = """你是儿童内容审核与编目专家。对下列 B 站视频逐条判断并打标。

判断"适合"的标准：
- 内容面向儿童或适合儿童观看：知识科普、动画、儿歌、绘本、手工、自然、生活习惯等
- 排除：暴力恐怖、成人化内容、软广带货、标题党口水内容、纯游戏实况、成人向吐槽
- 主题相关的 UP 主讲解类（如科普长视频）可放宽到 6-9/9-12 岁

年龄段枚举：{ages}
语言枚举：{langs}（中文视频含少量英文单词仍算 zh；英语教学内容标 en 或 bilingual）
主题枚举：{themes}（每条 1-3 个，按主要从属）

视频列表（JSON 数组，字段：bvid/title/up/desc）：
{items}

只输出 JSON 数组，每个元素形如：
{{"bvid":"...","suitable":true,"age":["3-6"],"language":["zh"],"theme":["science"],"note":"一句话理由"}}
suitable=false 时 age/language/theme 给空数组。不要输出 JSON 以外的任何文字。"""


def call_llm(messages, base_url, api_key, model, retries=3):
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  ! LLM 调用失败（第 {attempt + 1} 次）: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("LLM 调用连续失败")


def parse_json_block(text):
    """模型偶尔包 markdown 代码围栏，剥掉再解析。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def validate(entry):
    """校验并收敛一条 LLM 输出；不合规字段丢弃。"""
    tags = {}
    for key, allowed in (("age", AGE_IDS), ("language", LANG_IDS), ("theme", THEME_IDS)):
        vals = entry.get(key) or []
        tags[key] = [v for v in vals if v in allowed]
    return {
        "bvid": entry.get("bvid"),
        "suitable": bool(entry.get("suitable")) and all(tags.values()),
        "note": str(entry.get("note") or "")[:120],
        "tags": tags,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=ROOT / "data/candidates.json")
    ap.add_argument("--output", type=Path, default=ROOT / "data/tagged.json")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        sys_exit = "请设置 LLM_API_KEY"
        raise SystemExit(sys_exit)
    base_url = os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    model = os.environ.get("LLM_MODEL", "glm-4-flash")

    cands = json.loads(args.input.read_text(encoding="utf-8"))["videos"]
    # 只富化过的（有 desc/title）才进入打标
    cands = [v for v in cands if v.get("title")]

    done = {}
    if args.output.exists():
        for row in json.loads(args.output.read_text(encoding="utf-8"))["videos"]:
            done[row["bvid"]] = row
    todo = [v for v in cands if v["bvid"] not in done]
    print(f"候选 {len(cands)}，已完成 {len(done)}，待打标 {len(todo)}")

    results = list(done.values())
    batches = [todo[i : i + args.batch_size] for i in range(0, len(todo), args.batch_size)]
    if args.dry_run:
        batches = batches[:3]

    prompt_header = PROMPT_TEMPLATE.format(
        ages="/".join(AGE_IDS),
        langs="/".join(LANG_IDS),
        themes="/".join(THEME_IDS),
        items="{items}",
    )
    for bi, batch in enumerate(batches):
        items = json.dumps(
            [
                {
                    "bvid": v["bvid"],
                    "title": v.get("title"),
                    "up": v.get("up"),
                    "desc": (v.get("desc") or "")[:300],
                }
                for v in batch
            ],
            ensure_ascii=False,
        )
        messages = [
            {"role": "system", "content": "只输出合法 JSON。"},
            {"role": "user", "content": prompt_header.format(items=items)},
        ]
        try:
            raw = call_llm(messages, base_url, api_key, model)
            rows = parse_json_block(raw)
            if isinstance(rows, dict):
                rows = rows.get("videos") or rows.get("results") or []
        except (ValueError, RuntimeError) as e:
            print(f"  ! 批次 {bi} 解析失败，跳过: {e}", flush=True)
            continue
        by_bvid = {r.get("bvid"): r for r in rows if isinstance(r, dict)}
        kept = 0
        for v in batch:
            if v["bvid"] in by_bvid:
                entry = validate(by_bvid[v["bvid"]])
                entry["bvid"] = v["bvid"]
                results.append(entry)
                done[v["bvid"]] = entry
                kept += 1
        print(f"批次 {bi + 1}/{len(batches)}：{kept}/{len(batch)} 条打标完成", flush=True)
        # 增量写盘 = 断点续跑
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {"schema_version": 1, "count": len(results), "videos": results},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    suitable = sum(1 for r in results if r["suitable"])
    print(f"\n完成：{len(results)} 条打标，其中适宜 {suitable} 条 → {args.output}")


if __name__ == "__main__":
    main()
