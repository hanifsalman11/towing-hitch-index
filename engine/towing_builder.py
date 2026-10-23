import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/towing-hitch-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6").strip()
CUSTOM_VEHICLE = os.environ.get("CUSTOM_VEHICLE", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_vehicles.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Vehicle Model & Engine, Max Towing lbs, Max Payload lbs, GVWR lbs, Hitch Class, Axle Ratio)
SEED_VEHICLES = [
    ("Ford F-150 3.5L EcoBoost V6 Crew Cab 4x4", 13500, 2445, 7100, "Class IV (2-Inch)", "3.55 Electronic Locking"),
    ("Ford F-150 5.0L Coyote V8 SuperCrew 4x4", 12900, 2225, 7050, "Class IV (2-Inch)", "3.73 Electronic Locking"),
    ("Chevrolet Silverado 1500 5.3L EcoTec3 V8", 11300, 2080, 7100, "Class IV (2-Inch)", "3.42 Rear Axle"),
    ("Chevrolet Silverado 1500 3.0L Duramax Turbo-Diesel", 13300, 1970, 7200, "Class IV (2-Inch)", "3.73 Rear Axle"),
    ("Ram 1500 3.0L Hurricane High-Output I6", 11550, 1980, 7100, "Class IV (2-Inch)", "3.92 Anti-Spin"),
    ("Ram 1500 5.7L HEMI V8 eTorque Crew Cab", 12750, 1890, 7100, "Class IV (2-Inch)", "3.92 Anti-Spin"),
    ("Toyota Tundra 3.4L i-FORCE Twin-Turbo V6", 12000, 1885, 7385, "Class IV (2-Inch)", "3.31 Rear Axle"),
    ("Toyota Tacoma 2.4L i-FORCE Turbo 4WD", 6500, 1500, 6005, "Class IV (2-Inch)", "3.58 Rear Axle"),
    ("Toyota 4Runner i-FORCE MAX Hybrid 4WD", 6000, 1450, 6150, "Class III/IV (2-Inch)", "3.73 Rear Axle"),
    ("Ford F-250 Super Duty 6.7L Power Stroke Diesel", 20000, 3450, 10000, "Class V (2.5-Inch / 3-Inch)", "3.55 Electronic Locking"),
    ("Ford F-250 Super Duty 7.3L Godzilla V8", 17200, 4160, 10000, "Class V (2.5-Inch)", "4.30 Electronic Locking"),
    ("Chevrolet Silverado 2500HD 6.6L Duramax Diesel", 20000, 3689, 10850, "Class V (2.5-Inch)", "3.42 Rear Axle"),
    ("GMC Sierra 1500 6.2L EcoTec3 V8 AT4", 13000, 1820, 7100, "Class IV (2-Inch)", "3.23 Rear Axle"),
    ("Jeep Grand Cherokee L 3.6L Pentastar V6", 6200, 1380, 6500, "Class IV (2-Inch)", "3.45 Rear Axle"),
    ("Jeep Wrangler Unlimited Rubicon 3.6L V6", 5000, 1150, 6100, "Class III (2-Inch)", "4.10 Dana 44 HD"),
    ("Jeep Gladiator Mojave / Rubicon 3.6L V6", 7700, 1530, 6250, "Class IV (2-Inch)", "4.10 Heavy-Duty"),
    ("Chevrolet Tahoe 5.3L V8 Max Trailering", 8400, 1834, 7500, "Class IV (2-Inch)", "3.42 Rear Axle"),
    ("Ford Expedition 3.5L EcoBoost Heavy-Duty Tow", 9300, 1750, 7450, "Class IV (2-Inch)", "3.73 Rear Axle"),
    ("Ford Ranger 2.7L EcoBoost V6 4x4", 7500, 1711, 6170, "Class IV (2-Inch)", "3.73 Electronic Locking"),
    ("Chevrolet Colorado Trail Boss 2.7L TurboMax", 7700, 1587, 6250, "Class IV (2-Inch)", "3.42 Rear Axle"),
    ("Nissan Pathfinder Rock Creek 3.5L V6", 6000, 1350, 6063, "Class III (2-Inch)", "4.33 Direct Coupling"),
    ("Honda Pilot TrailSport 3.5L V6 AWD", 5000, 1325, 6195, "Class III (2-Inch)", "4.167 i-VTM4"),
    ("Subaru Outback Wilderness 2.4L Turbo Boxer", 3500, 950, 5026, "Class III (2-Inch)", "4.44 Final Drive"),
    ("Toyota Sequoia 3.4L i-FORCE MAX Hybrid", 9520, 1520, 7615, "Class IV (2-Inch)", "3.31 Rear Axle"),
    ("Dodge Durango R/T 5.7L HEMI Tow N Go", 8700, 1420, 7100, "Class IV (2-Inch)", "3.09 Rear Axle"),
    ("GMC Canyon AT4 2.7L TurboMax", 7700, 1550, 6250, "Class IV (2-Inch)", "3.42 Rear Axle"),
    ("Ram 2500 6.7L Cummins Turbo Diesel", 19990, 3140, 10000, "Class V (2.5-Inch)", "3.73 Anti-Spin"),
    ("Lexus GX 550 Overtrail+ 3.4L Twin-Turbo V6", 9096, 1480, 7010, "Class IV (2-Inch)", "3.307 Torsen Limited-Slip"),
    ("Rivian R1T Dual-Motor Max Pack Truck", 11000, 1764, 8532, "Class IV (2-Inch)", "Dual Permanent Magnet"),
    ("Ford Maverick 2.0L EcoBoost AWD 4K Tow", 4000, 1500, 5200, "Class III (2-Inch)", "3.81 Final Drive")
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=7500.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_towing_queries():
    """Mengambil kueri model kendaraan & kalkulator towing dari Google Autocomplete US."""
    discovered = []
    seeds = [
        "towing capacity calculator for ",
        "weight distribution hitch for ",
        "tongue weight limit for ",
        "can a tow a camper "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(towing|capacity|calculator|weight|distribution|hitch|tongue|limit|for|specs)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        discovered.append((cleaned.title(), 8500, 1750, 6800, "Class IV (2-Inch)", "3.55 Rear Axle"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_towing_data(veh_tuple):
    """Mesin Fisika Beban Gandar SAE J2807 & Payload Margin (100% bebas gagal)."""
    veh_name, max_tow, max_payload, gvwr, hitch_class, axle_ratio = veh_tuple

    # Safe real-world loaded camper target = 80% of max rated tow capacity
    safe_80pct_tow = int(round(max_tow * 0.80, -2))
    # Standard travel trailer tongue weight = 13% of loaded trailer weight
    est_tongue_lbs = int(round(safe_80pct_tow * 0.13))
    # WDH Hardware weight ~90 lbs
    remaining_cabin_payload = max(250, max_payload - est_tongue_lbs - 90)

    if est_tongue_lbs >= 1100:
        wdh_bar_rating = "1,200 lb – 1,500 lb Trunnion Bar Weight Distribution Hitch"
        wdh_query = "Weight Distribution Hitch Sway Control 1200 lb 14000 lb"
        wdh_price = "$489 - $799"
        shank_size = "2.5-Inch or 2-Inch Heavy-Duty Forged Shank"
    elif est_tongue_lbs >= 750:
        wdh_bar_rating = "1,000 lb Spring Bar Weight Distribution Hitch with 4-Point Sway Control"
        wdh_query = "Weight Distribution Hitch Sway Control 1000 lb Tongue 10000 lb"
        wdh_price = "$379 - $649"
        shank_size = "2-Inch Solid Steel Forged Shank"
    else:
        wdh_bar_rating = "600 lb – 800 lb Light-Duty Weight Distribution & Anti-Sway Hitch"
        wdh_query = "Weight Distribution Hitch Sway Control 800 lb Tongue 8000 lb"
        wdh_price = "$289 - $499"
        shank_size = "2-Inch Standard Receiver Shank"

    return {
        "vehicle_name": veh_name,
        "seo_title": f"{veh_name} Towing Capacity, Payload & Hitch Sizing Calculator (2026)",
        "meta_description": f"Calculate exact safe camper weight ({safe_80pct_tow:,} lbs), 13% tongue weight ({est_tongue_lbs:,} lbs), payload margin ({max_payload:,} lbs), and Weight Distribution Hitch size for the {veh_name}.",
        "specs": {
            "max_towing_lbs": max_tow,
            "max_payload_lbs": max_payload,
            "gvwr_lbs": gvwr,
            "safe_80pct_trailer_lbs": safe_80pct_tow,
            "target_13pct_tongue_lbs": est_tongue_lbs,
            "hitch_class": hitch_class,
            "axle_ratio": axle_ratio
        },
        "engineering_verdict": f"Rated under SAE J2807 standards at up to {max_tow:,} lbs maximum towing capacity and {max_payload:,} lbs payload ({gvwr:,} lbs GVWR), the {veh_name} usually hits its door-jamb payload ceiling before reaching its maximum tow rating. Pulling a loaded {safe_80pct_tow:,} lb travel trailer places ~{est_tongue_lbs:,} lbs of tongue weight (13%) plus ~90 lbs of hitch hardware onto the rear receiver, leaving {remaining_cabin_payload:,} lbs of safe payload capacity for passengers and truck-bed cargo.",
        "hardware_bundle": [
            {
                "badge": "Matched WDH & Sway Kit",
                "title": wdh_bar_rating,
                "price_range": wdh_price,
                "amazon_query": wdh_query,
                "tow_note": f"Restores front steering axle downforce and eliminates highway crosswind trailer sway for {safe_80pct_tow:,} lb campers."
            },
            {
                "badge": "Built-In Tongue Scale Hitch",
                "title": f"Adjustable Aluminum Drop Hitch with Integrated Hydraulic Tongue Weight Gauge ({shank_size})",
                "price_range": "$219 - $349",
                "amazon_query": "Weigh Safe Adjustable Aluminum Drop Hitch Built In Scale 2 Inch",
                "tow_note": "Measures exact real-time tongue weight (target 10%–15% of GTW) every time you hook up your trailer."
            },
            {
                "badge": "Proportional Brake Control",
                "title": "3-Axis Accelerometer Proportional Electronic Trailer Brake Controller + Plug-and-Play Harness",
                "price_range": "$129 - $239",
                "amazon_query": "Tekonsha Prodigy P3 Proportional Trailer Brake Controller",
                "tow_note": "Automatically applies trailer electric brakes in direct proportion to tow vehicle deceleration G-force."
            },
            {
                "badge": "Trailer TPMS & Rear Cam",
                "title": "Solar RV 4/6-Wheel Tire Pressure & Temperature Monitor (TPMS) + Magnetic Hitch Camera",
                "price_range": "$119 - $249",
                "amazon_query": "RV Trailer Tire Pressure Monitoring System TPMS Solar 6 Sensor",
                "tow_note": "Prevents catastrophic trailer tire blowouts by alerting cabin display to rapid pressure loss or hub overheating."
            }
        ],
        "safety_checklist": [
            f"Verify your specific vehicle's Yellow Tire & Loading Information sticker inside the driver's door jamb; real-world payload is often 150–300 lbs lower than the {max_payload:,} lb brochure maximum due to factory options.",
            f"Maintain trailer tongue weight strictly between 12% and 14% of loaded trailer weight (~{est_tongue_lbs:,} lbs for a {safe_80pct_tow:,} lb camper) to prevent high-speed fishtailing.",
            "Measure front fender wheel-well height before hitching and adjust your Weight Distribution Hitch spring bars until at least 50% to 100% of front-axle rise is restored.",
            "Perform a 15-mph manual override slide test on your proportional trailer brake controller in an empty parking lot before entering highway traffic."
        ],
        "faqs": [
            {
                "q": f"What is the realistic camper weight a {veh_name} can safely tow?",
                "a": f"While the maximum brochure tow rating is {max_tow:,} lbs, experienced towing engineers follow the 80% safety rule ({safe_80pct_tow:,} lbs loaded GVWR). At {safe_80pct_tow:,} lbs, the 13% tongue weight is {est_tongue_lbs:,} lbs, keeping you safely inside the {max_payload:,} lb rear axle/payload limit."
            },
            {
                "q": f"Do I need a Weight Distribution Hitch (WDH) on the {veh_name}?",
                "a": f"Yes. Most {hitch_class} factory receivers are rated for only 500 lbs of dead-weight tongue load (5,000 lb trailer) without weight distribution. Any trailer exceeding 5,000 lbs requires a {wdh_bar_rating}."
            },
            {
                "q": f"How does passenger and cargo weight affect towing capacity on the {veh_name}?",
                "a": f"Every pound of tongue weight ({est_tongue_lbs:,} lbs) and hitch hardware (~90 lbs) is subtracted directly from your {max_payload:,} lb truck payload rating. If you carry {remaining_cabin_payload:,}+ lbs of passengers, firewood, and coolers in the truck, you must reduce trailer tongue weight accordingly."
            }
        ]
    }


def generate_towing_data(veh_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic SAE J2807 Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_towing_data(veh_tuple)

    veh_name, max_tow, max_payload, gvwr, hitch_class, axle_ratio = veh_tuple
    safe_80pct_tow = int(round(max_tow * 0.80, -2))
    est_tongue_lbs = int(round(safe_80pct_tow * 0.13))

    prompt = f"""
You are a Senior SAE J2807 Automotive Towing & Chassis Dynamics Engineer. Create an accurate 2026 towing capacity, tongue weight, payload margin, and Weight Distribution Hitch sizing guide for: "{veh_name}".
Baseline reference specs: Max Towing={max_tow} lbs, Max Payload={max_payload} lbs, GVWR={gvwr} lbs, Safe 80% Trailer={safe_80pct_tow} lbs, 13% Tongue Weight={est_tongue_lbs} lbs, Hitch={hitch_class}, Axle={axle_ratio}.
Return ONLY a valid JSON object matching this exact schema:
{{
  "vehicle_name": "{veh_name}",
  "seo_title": "{veh_name} Towing Capacity, Payload & Hitch Sizing Calculator (2026)",
  "meta_description": "Calculate exact safe travel trailer weight, 13% tongue weight, payload margin, and Weight Distribution Hitch spring bar rating for the {veh_name}.",
  "specs": {{
    "max_towing_lbs": {max_tow},
    "max_payload_lbs": {max_payload},
    "gvwr_lbs": {gvwr},
    "safe_80pct_trailer_lbs": {safe_80pct_tow},
    "target_13pct_tongue_lbs": {est_tongue_lbs},
    "hitch_class": "{hitch_class}",
    "axle_ratio": "{axle_ratio}"
  }},
  "engineering_verdict": "3-sentence technical summary stating max towing, payload, why payload limits camper size before max towing, and exact remaining payload with a 13% tongue weight.",
  "hardware_bundle": [
    {{
      "badge": "Matched WDH & Sway Kit",
      "title": "Exact Trunnion Bar Weight Distribution Hitch recommendation",
      "price_range": "$379 - $699",
      "amazon_query": "Weight Distribution Hitch Sway Control 1000 lb 10000 lb",
      "tow_note": "1-sentence front axle load restoration note"
    }},
    {{
      "badge": "Built-In Scale Drop Hitch",
      "title": "Adjustable Aluminum Drop Hitch with Integrated Tongue Weight Scale",
      "price_range": "$219 - $349",
      "amazon_query": "Weigh Safe Adjustable Drop Hitch Built In Scale",
      "tow_note": "1-sentence 10%-15% tongue balance note"
    }},
    {{
      "badge": "Proportional Brake Control",
      "title": "Proportional Electronic Trailer Brake Controller",
      "price_range": "$129 - $239",
      "amazon_query": "Tekonsha Prodigy P3 Proportional Trailer Brake Controller",
      "tow_note": "1-sentence braking safety note"
    }},
    {{
      "badge": "RV Trailer TPMS Monitor",
      "title": "Solar RV 6-Sensor Tire Pressure & Hub Temperature Monitoring System",
      "price_range": "$119 - $229",
      "amazon_query": "RV Trailer TPMS Tire Pressure Monitoring System 6 Sensor",
      "tow_note": "1-sentence blowout prevention note"
    }}
  ],
  "safety_checklist": [
    "Step 1 regarding driver door-jamb yellow payload sticker verification",
    "Step 2 regarding 12%-14% tongue weight balancing",
    "Step 3 regarding WDH front fender height measurement",
    "Step 4 regarding proportional brake controller gain calibration"
  ],
  "faqs": [
    {{"q": "What is the realistic camper weight a {veh_name} can safely tow?", "a": "Exact lbs comparing brochure max vs 80% rule and payload limit."}},
    {{"q": "Do I need a Weight Distribution Hitch on the {veh_name}?", "a": "Direct answer explaining 500 lb dead-weight receiver limits."}},
    {{"q": "How much tongue weight can the {veh_name} handle?", "a": "Exact lbs calculation subtracting passengers and cargo from payload."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{veh_name}': {e}")

    return build_deterministic_towing_data(veh_tuple)


def build_towing_html_page(data, slug, mon_cfg):
    veh_name = data.get("vehicle_name", "Tow Vehicle")
    sp = data.get("specs", {})
    max_tow = int(safe_float(sp.get("max_towing_lbs", 10000), 10000))
    max_payload = int(safe_float(sp.get("max_payload_lbs", 1850), 1850))
    gvwr = int(safe_float(sp.get("gvwr_lbs", 7100), 7100))
    safe_80_tow = int(safe_float(sp.get("safe_80pct_trailer_lbs", int(max_tow * 0.8)), int(max_tow * 0.8)))
    hitch_class = sp.get("hitch_class", "Class IV (2-Inch)")
    axle_ratio = sp.get("axle_ratio", "3.55 Rear Axle")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Weight+Distribution+Hitch+Sway+Control"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{veh_name} Towing Capacity & Hitch Sizing Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Weight Distribution Hitch")), mon_cfg)
        bundle_html += f"""
        <div class="bg-stone-900 border border-stone-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Towing Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$129+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-stone-400 mt-2 leading-relaxed">🛻 {item.get('tow_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Camper Weight vs Payload Margin Reference Table
    matrix_rows_html = ""
    for pct in [0.50, 0.65, 0.75, 0.85, 0.95, 1.00]:
        t_wt = int(round(max_tow * pct, -2))
        tw_13 = int(round(t_wt * 0.13))
        wdh_wt = 90 if t_wt > 5000 else 0
        rem_pay = max_payload - tw_13 - wdh_wt
        status_badge = (
            f"<span class='text-emerald-400 font-bold'>+{rem_pay:,} lbs Safe</span>"
            if rem_pay >= 450
            else (
                f"<span class='text-amber-400 font-bold'>+{rem_pay:,} lbs Tight</span>"
                if rem_pay >= 150
                else f"<span class='text-red-400 font-bold'>{rem_pay:,} lbs Payload Risk</span>"
            )
        )
        bar_spec = "No WDH Needed" if t_wt <= 4500 else ("800 lb Bars" if tw_13 <= 750 else ("1,000 lb Bars" if tw_13 <= 1000 else "1,200–1,500 lb Bars"))
        matrix_rows_html += f"""
        <tr class="border-b border-stone-800 hover:bg-stone-800/40">
          <td class="py-3 px-4 font-bold text-white">{t_wt:,} lbs ({int(pct*100)}%)</td>
          <td class="py-3 px-4 text-amber-400 font-semibold">{tw_13:,} lbs</td>
          <td class="py-3 px-4">{status_badge}</td>
          <td class="py-3 px-4 text-xs text-stone-300 font-semibold">{bar_spec}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("safety_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-stone-900 border border-stone-800 rounded-xl p-4 cursor-pointer hover:border-stone-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer tow-check">
          <span class="text-sm text-stone-200 leading-relaxed"><strong>Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-stone-900 border border-stone-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-stone-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', veh_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', veh_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-stone-950 text-stone-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-stone-800 bg-stone-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-stone-950 px-2 py-0.5 rounded font-black">TOW</span>HitchIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Weight Distribution Hitches →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-stone-950 px-3 py-1 rounded-full">Max Tow: {max_tow:,} lbs</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Payload: {max_payload:,} lbs | GVWR: {gvwr:,} lbs</span>
        <span class="text-xs font-semibold bg-stone-800 text-stone-300 px-3 py-1 rounded-full">{hitch_class} | {axle_ratio}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', veh_name)}</h1>
      <div class="mt-4 bg-stone-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-stone-200 leading-relaxed">
        <strong>SAE J2807 Chassis & Payload Verdict:</strong> {data.get('engineering_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE TOWING, TONGUE WEIGHT & PAYLOAD MARGIN CALCULATOR -->
    <section class="bg-stone-900 border border-stone-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {veh_name} Tongue Weight & Payload Calculator</h2>
      <p class="text-xs text-stone-400 mb-6">Slide your loaded trailer weight (GVWR), passenger/cargo weight inside the vehicle, and tongue weight percentage to check real-time axle payload safety and required WDH spring bar rating.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="trailerSlider" class="text-stone-300">Loaded Trailer Gross Weight (lbs)</label>
              <span class="text-amber-400 font-bold"><span id="trailerVal">{safe_80_tow:,}</span> lbs</span>
            </div>
            <input id="trailerSlider" type="range" min="1500" max="{int(max_tow + 2000)}" step="100" value="{safe_80_tow}" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="cargoSlider" class="text-stone-300">Passengers, Pets & Truck Bed Cargo (lbs)</label>
              <span class="text-amber-400 font-bold"><span id="cargoVal">450</span> lbs</span>
            </div>
            <input id="cargoSlider" type="range" min="150" max="1800" step="25" value="450" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="twPctSlider" class="text-stone-300">Tongue Weight Ratio (Standard Camper = 13%)</label>
              <span class="text-amber-400 font-bold"><span id="twPctVal">13</span>%</span>
            </div>
            <input id="twPctSlider" type="range" min="10" max="15" step="1" value="13" class="w-full accent-amber-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-stone-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Pin / Tongue Weight</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="tongueOut">0</span> <span class="text-sm font-normal text-stone-400">lbs</span></div>
            <p id="wdhBarOut" class="text-xs text-amber-400 font-semibold mt-1">Need 1,000 lb WDH Bars</p>
          </div>

          <div class="bg-stone-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Remaining Payload</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1"><span id="payloadMarginOut">0</span> <span class="text-sm font-normal text-stone-400">lbs</span></div>
            <p id="safetyStatusOut" class="text-xs text-emerald-400 font-semibold mt-1">✅ Within GVWR & Tow Limit</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="hitchAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicHitchBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched WDH Kit on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Recommended Towing & Hitch Hardware for {veh_name}</h2>
        <span class="text-xs text-stone-400">SAE J684 & V-5 Rated Equipment</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- CAMPER WEIGHT MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{veh_name} Trailer Weight vs. Payload Margin Chart</h2>
      <div class="overflow-x-auto bg-stone-900 border border-stone-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-stone-800 bg-stone-950/60 text-stone-400 uppercase text-xs">
              <th class="py-3.5 px-4">Loaded Trailer Weight</th>
              <th class="py-3.5 px-4 text-amber-400">13% Tongue Weight</th>
              <th class="py-3.5 px-4">Cabin Payload Left (after WDH)</th>
              <th class="py-3.5 px-4">Required WDH Spring Bars</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- SAFETY CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Pre-Trip Weight Distribution & Brake Setup Checklist</h2>
        <span id="towBadge" class="text-xs font-bold bg-stone-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({veh_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-stone-800 py-8 text-center text-xs text-stone-500 px-4">
    <p>© {datetime.now(timezone.utc).year} TowHitchIndex. Independent SAE J2807 Towing & Payload Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const maxTowLbs = {max_tow};
    const maxPayloadLbs = {max_payload};
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const trailerSlider = document.getElementById('trailerSlider');
    const cargoSlider = document.getElementById('cargoSlider');
    const twPctSlider = document.getElementById('twPctSlider');
    const trailerVal = document.getElementById('trailerVal');
    const cargoVal = document.getElementById('cargoVal');
    const twPctVal = document.getElementById('twPctVal');
    const tongueOut = document.getElementById('tongueOut');
    const wdhBarOut = document.getElementById('wdhBarOut');
    const payloadMarginOut = document.getElementById('payloadMarginOut');
    const safetyStatusOut = document.getElementById('safetyStatusOut');
    const hitchAdviceBanner = document.getElementById('hitchAdviceBanner');
    const dynamicHitchBtn = document.getElementById('dynamicHitchBtn');

    function recalculateTow() {{
      const trailerLbs = parseInt(trailerSlider.value, 10);
      const cargoLbs = parseInt(cargoSlider.value, 10);
      const twPct = parseInt(twPctSlider.value, 10);

      trailerVal.textContent = trailerLbs.toLocaleString();
      cargoVal.textContent = cargoLbs.toLocaleString();
      twPctVal.textContent = twPct;

      const tongueLbs = Math.round(trailerLbs * (twPct / 100.0));
      const wdhHardwareLbs = trailerLbs > 5000 ? 90 : 25;
      const totalPayloadUsed = tongueLbs + cargoLbs + wdhHardwareLbs;
      const payloadRemaining = maxPayloadLbs - totalPayloadUsed;

      tongueOut.textContent = tongueLbs.toLocaleString();
      payloadMarginOut.textContent = payloadRemaining.toLocaleString();

      let barRating = "800 lb";
      if (tongueLbs <= 600) barRating = "600 lb";
      else if (tongueLbs <= 800) barRating = "800 lb";
      else if (tongueLbs <= 1000) barRating = "1,000 lb";
      else if (tongueLbs <= 1200) barRating = "1,200 lb";
      else barRating = "1,500 lb";

      wdhBarOut.textContent = trailerLbs > 5000 ? `Need ${{barRating}} WDH Bars` : `Standard Ball Mount OK`;

      if (trailerLbs > maxTowLbs) {{
        safetyStatusOut.textContent = `❌ Exceeds Max Tow by ${{(trailerLbs - maxTowLbs).toLocaleString()}} lbs!`;
        safetyStatusOut.className = "text-xs text-red-400 font-bold mt-1";
      }} else if (payloadRemaining < 0) {{
        safetyStatusOut.textContent = `⚠️ Over Payload by ${{Math.abs(payloadRemaining).toLocaleString()}} lbs!`;
        safetyStatusOut.className = "text-xs text-amber-400 font-bold mt-1";
      }} else {{
        safetyStatusOut.textContent = `✅ Safe (+${{payloadRemaining.toLocaleString()}} lbs Payload Buffer)`;
        safetyStatusOut.className = "text-xs text-emerald-400 font-semibold mt-1";
      }}

      const barClean = barRating.replace(',', '');
      hitchAdviceBanner.innerHTML = `🛻 <strong>Required Hitch Setup:</strong> A ${{trailerLbs.toLocaleString()}} lb trailer produces <strong>${{tongueLbs.toLocaleString()}} lbs of tongue weight</strong>. Pair with a <strong>${{barRating}} Trunnion Weight Distribution & Sway Control Hitch</strong>.`;
      dynamicHitchBtn.href = `https://${{amzDomain}}/s?k=Weight+Distribution+Hitch+Sway+Control+${{encodeURIComponent(barClean)}}+Tongue&tag=${{amzTag}}`;
    }}

    trailerSlider.addEventListener('input', recalculateTow);
    cargoSlider.addEventListener('input', recalculateTow);
    twPctSlider.addEventListener('input', recalculateTow);
    recalculateTow();

    const checks = document.querySelectorAll('.tow-check');
    const badge = document.getElementById('towBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Weight+Distribution+Hitch+Sway+Control"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-stone-900 border border-stone-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-stone-950 px-2.5 py-0.5 rounded">Max Tow: {item.get('max_tow', 10000):,} lbs</span>
            <span class="text-xs text-stone-400">Payload: {item.get('max_payload', 1800):,} lbs</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['vehicle_name']} Towing & Hitch Calculator</h2>
          <p class="text-xs text-stone-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate Tongue Weight & WDH Size →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TowHitchIndex — Truck & SUV Towing Capacity, Payload & WDH Sizing Calculator (2026)</title>
  <meta name="description" content="Calculate exact travel trailer tongue weight, remaining cabin payload margin, and Weight Distribution Hitch spring bar ratings for Ford, Chevy, Ram, Toyota, GMC, and Jeep vehicles.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="TowHitchIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-950 text-stone-100 min-h-screen flex flex-col">
  <header class="border-b border-stone-800 bg-stone-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-stone-950 px-2 py-0.5 rounded font-black">TOW</span>HitchIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-stone-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Weight Distribution Hitches →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Truck & SUV Towing, Payload & Hitch Sizing Database</h1>
      <p class="text-stone-400 mt-3 text-base sm:text-lg">Select your truck or SUV below to calculate safe camper weight (80% rule), 13% tongue weight vs. door-jamb payload margin, and required Weight Distribution Hitch spring bar rating.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search truck or SUV (e.g. F-150 EcoBoost, Silverado 1500, Ram 1500, Tacoma, Tahoe, Tundra...)" class="w-full bg-stone-900 border border-stone-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="vehGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-stone-800 py-8 text-center text-xs text-stone-500">
    <p>© {datetime.now(timezone.utc).year} TowHitchIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('vehGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>TowHitchIndex SAE J2807 Towing & Payload Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Truck & SUV Towing Capacity, Tongue Weight & Hitch Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_VEHICLE:
        candidates.append((CUSTOM_VEHICLE.strip(), 9500, 1850, 7000, "Class IV (2-Inch)", "3.55 Rear Axle"))
    candidates.extend(SEED_VEHICLES)
    candidates.extend(discover_google_towing_queries())

    new_urls = []
    count = 0

    for veh_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        veh_name = veh_tuple[0]
        slug = slugify(f"{veh_name}-towing-payload-hitch-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating SAE J2807 towing & WDH calculator for: {veh_name}...")
        try:
            data = generate_towing_data(veh_tuple)
            build_towing_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "vehicle_name": data.get("vehicle_name", veh_name),
                "slug": slug,
                "title": data.get("seo_title", f"{veh_name} Towing Calculator"),
                "description": data.get("meta_description", ""),
                "max_tow": int(safe_float(sp.get("max_towing_lbs", veh_tuple[1]), veh_tuple[1])),
                "max_payload": int(safe_float(sp.get("max_payload_lbs", veh_tuple[2]), veh_tuple[2])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {veh_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new towing & hitch calculator pages.")


if __name__ == "__main__":
    main()
