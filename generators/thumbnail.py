#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
themes.txt の各行: <layout> | <theme>
layout: square / landscape / portrait
  ① gpt-4o-mini で YAML 最適化
  ② gpt-image-1 (Low 品質) で画像生成
  ③ トークン数と画像単価からコスト計算 → CSV ログ
"""

import os, re, time, csv, base64, requests, datetime
from pathlib import Path
from dotenv import load_dotenv
import openai

# ------------------------------------------------------------------
# 0. パス定義
# ------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts"
OUT_P_DIR   = ROOT / "outputs" / "prompts"
OUT_I_DIR   = ROOT / "outputs" / "images"
LOG_DIR     = ROOT / "logs"
for d in (OUT_P_DIR, OUT_I_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

SYSTEM_TEXT = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")
THEMES_TXT  = ROOT / "themes.txt"

# ------------------------------------------------------------------
# 画像の品質と単価（USD）
# ------------------------------------------------------------------
QUALITY = "low"        # ← medium / high に変える場合はここを修正
IMG_COST_USD = {
    ("low",  "1024x1024"): 0.011,
    ("low",  "1024x1536"): 0.016,
    ("low",  "1536x1024"): 0.016,
    ("medium", "1024x1024"): 0.042,
    ("medium", "1024x1536"): 0.063,
    ("medium", "1536x1024"): 0.063,
    ("high", "1024x1024"): 0.167,
    ("high", "1024x1536"): 0.25,
    ("high", "1536x1024"): 0.25,
}

TEMPLATE_MAP = {
    "square":    ("base_square.yaml",    "1024x1024"),
    "landscape": ("base_landscape.yaml", "1536x1024"),
    "portrait":  ("base_portrait.yaml",  "1024x1536"),
}

# gpt-4o-mini 料金（USD/1M tokens）
PRICE_IN  = 0.15
PRICE_OUT = 0.60

# ------------------------------------------------------------------
# 1. OpenAI 認証
# ------------------------------------------------------------------
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise EnvironmentError(".env に OPENAI_API_KEY がありません")

# ------------------------------------------------------------------
# 2. テーマ一覧を取得
# ------------------------------------------------------------------
lines = [l.strip() for l in THEMES_TXT.read_text(encoding="utf-8").splitlines() if l.strip()]
if not lines:
    raise ValueError("themes.txt が空です。<layout> | <theme> を書いてください。")

# ------------------------------------------------------------------
# 3. CSV ログ準備
# ------------------------------------------------------------------
today = datetime.date.today().strftime("%Y%m%d")
log_path = LOG_DIR / f"cost_log_{today}.csv"
is_new   = not log_path.exists()
with open(log_path, "a", newline="", encoding="utf-8") as csv_f:
    writer = csv.writer(csv_f)
    if is_new:
        writer.writerow([
            "timestamp", "layout", "theme",
            "input_tok", "output_tok", "chat_cost($)",
            "image_size", "image_cost($)", "total_cost($)"
        ])

    total_cost = 0.0

    # ------------------------------------------------------------------
    # 4. メインループ
    # ------------------------------------------------------------------
    for idx, raw in enumerate(lines, 1):
        layout, theme = [s.strip() for s in raw.split("|", 1)]
        if layout not in TEMPLATE_MAP:
            raise ValueError(f"layout '{layout}' は square / landscape / portrait のいずれかで指定してください")

        yaml_file, img_size = TEMPLATE_MAP[layout]
        BASE_YAML = (PROMPTS_DIR / yaml_file).read_text(encoding="utf-8")

        print(f"[{idx}/{len(lines)}] {layout} → {theme}")

        # ---- 4-A) YAML 最適化 ----
        chat_messages = [
            {"role": "system", "content": SYSTEM_TEXT},
            {"role": "user",
             "content": f"### TEMPLATE_YAML\n{BASE_YAML}\n\n### THEME\n{theme}"}
        ]
        rsp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=chat_messages,
            temperature=0.75
        )
        usage      = rsp.usage
        in_tok     = usage.prompt_tokens
        out_tok    = usage.completion_tokens
        chat_cost  = (in_tok / 1_000_000) * PRICE_IN + (out_tok / 1_000_000) * PRICE_OUT
        yaml_text  = re.sub(r"^```(?:yaml)?|```$", "",
                            rsp.choices[0].message.content.strip(),
                            flags=re.MULTILINE).strip()

        safe_name = re.sub(r"[\\/:*?\"<>|]", "_", theme)
        (OUT_P_DIR / f"{safe_name}.yaml").write_text(yaml_text, encoding="utf-8")

        # ---- 4-B) 画像生成 ----
        try:
            img_rsp = openai.images.generate(
                model="gpt-image-1",
                prompt=yaml_text,
                n=1,
                size=img_size,
                quality=QUALITY          # Low / Medium / High
            )
            data0 = img_rsp.data[0]
            if getattr(data0, "url", None):
                img_bytes = requests.get(data0.url).content
            elif getattr(data0, "b64_json", None):
                img_bytes = base64.b64decode(data0.b64_json)
            else:
                raise ValueError("画像データが取得できませんでした")

            (OUT_I_DIR / f"{safe_name}.png").write_bytes(img_bytes)
            image_cost = IMG_COST_USD[(QUALITY, img_size)]
            print(f"   ✅  Chat ${chat_cost:.4f} + Image ${image_cost:.3f}")

        except Exception as e:
            print(f"   ❌  画像生成エラー: {e}")
            image_cost = 0.0

        # ---- 4-C) CSV 記録 ----
        total = chat_cost + image_cost
        writer.writerow([
            datetime.datetime.now().isoformat(timespec="seconds"),
            layout, theme, in_tok, out_tok,
            f"{chat_cost:.4f}", img_size, f"{image_cost:.3f}", f"{total:.4f}"
        ])
        total_cost += total
        time.sleep(1.2)

print(f"\n🧾 生成完了 — 今日の合計コスト: ${total_cost:.4f}  (詳細: {log_path.name})")
