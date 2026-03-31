import os
from PIL import Image, ImageDraw, ImageFont
import datetime

# --- CONFIGURATION DES CHEMINS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, 'fonts')
CERT_DIR = os.path.join(BASE_DIR, 'certificate')
OUTPUT_DIR = os.path.join(CERT_DIR, 'generated')

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_font(filename, size):
    path = os.path.join(FONTS_DIR, filename)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

def generate_certificate(language, student_name, level_number):
    
    today = datetime.date.today()

    # --- POLICES GÉNÉRALES ---
    font_latin_name = 'GreatVibes-Regular.ttf'
    font_date_latin = 'TS-Safaa-Medium.otf'
    
    # C'EST ICI LE CHANGEMENT : On utilise Safaa pour le niveau en anglais aussi
    font_level_en = 'TS-Safaa-Medium.otf' 

    # --- CONFIGURATION PAR LANGUE ---
    config = {
        # === CHINOIS ===
        'cn': {
            'template': 'chinese.png',
            'font_native': 'MaShanZheng-Regular.ttf',
            'level_map': {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"},
            
            # Options de Style
            'english_stroke_width': 1,  # Gras activé pour Safaa
            'native_stroke_width': 1,
            'date_nat_size': 55,
            
            'level_en_txt': f"Level: Chinese Level {level_number}",
            'level_nat_fmt': "级别：中文{}级",
            'date_nat_txt': f"阿尔及尔，{today.year}年 {today.month}月 {today.day}日",
            
            # --- POSITIONS ---
            'y_name': 750,        
            'y_level_en': 1038,
            'y_level_nat': 1098,
            'pos_date': (201, 1210), 
            'color': 'black'
        },
        
        # === CORÉEN ===
        'kr': {
            'template': 'korean.png',
            'font_native': 'NanumMyeongjo-Bold.ttf',
            'level_map': None,
            
            'english_stroke_width': 1,  # Gras activé pour Safaa
            'native_stroke_width': 1,
            'date_nat_size': 40,
            
            'level_en_txt': f"Level: Korean Level {level_number}",
            'level_nat_fmt': f"급수: 한국어 {level_number}급",
            'date_nat_txt': f"알제, {today.year}년 {today.month}월 {today.day}일",
            
            'y_name': 750, 
            'y_level_en': 1065,
            'y_level_nat': 1125,
            'pos_date': (220, 1221),
            'color': 'black'
        },
        
        # === JAPONAIS ===
        'jp': {
            'template': 'japanese.png',
            'font_native': 'YujiSyuku-Regular.ttf',
            'level_map': None,
            
            'english_stroke_width': 1,  # Gras activé pour Safaa
            'native_stroke_width': 1,
            'date_nat_size': 41,
            
            'level_en_txt': f"Level: Japanese Level {level_number}",
            'level_nat_fmt': f"レベル：日本語 {level_number}級",
            'date_nat_txt': f"アルジェ、{today.year}年 {today.month}月 {today.day}日",
            
            'y_name': 750,
            'y_level_en': 1020,
            'y_level_nat': 1075,
            'pos_date': (202, 1196),
            'color': 'black'
        }
    }

    if language not in config: return

    conf = config[language]
    template_path = os.path.join(CERT_DIR, conf['template'])
    
    # --- CHARGEMENT ---
    try:
        img = Image.open(template_path).convert("RGB")
    except FileNotFoundError:
        print(f"Image introuvable : {template_path}")
        return

    draw = ImageDraw.Draw(img)
    W, H = img.size
    center_x = W / 2

    # --- CHARGEMENT POLICES ---
    font_name = get_font(font_latin_name, 160)     
    
    # Taille ajustée à 48 pour Safaa (car elle est souvent plus petite que Nanum)
    font_lvl_en = get_font(font_level_en, 48)      
    
    font_lvl_nat = get_font(conf['font_native'], 60) 
    font_date_en = get_font(font_date_latin, 42)
    font_date_nat = get_font(conf['font_native'], conf.get('date_nat_size', 40))

    # --- DESSIN ---

    # 1. NOM
    draw.text((center_x, conf['y_name']), student_name, font=font_name, fill="black", anchor="mm")

    # 2. NIVEAU ANGLAIS (En Safaa maintenant)
    draw.text(
        (center_x, conf['y_level_en']), 
        conf['level_en_txt'], 
        font=font_lvl_en, 
        fill="black", 
        anchor="mm",
        stroke_width=conf.get('english_stroke_width', 0), # Le gras est appliqué ici
        stroke_fill="black"
    )
    
    # 3. NIVEAU NATIF
    if language == 'cn':
        cn_num = conf['level_map'].get(level_number, str(level_number))
        txt_nat = conf['level_nat_fmt'].format(cn_num)
    else:
        txt_nat = conf['level_nat_fmt']
    
    draw.text(
        (center_x, conf['y_level_nat']), 
        txt_nat, 
        font=font_lvl_nat, 
        fill="black", 
        anchor="mm", 
        stroke_width=conf.get('native_stroke_width', 0),
        stroke_fill="black"
    )

    # 4. DATE
    x_date, y_date_base = conf['pos_date']
    date_en_str = today.strftime("Algiers, %B %d, %Y")
    draw.text((x_date, y_date_base), date_en_str, font=font_date_en, fill="black", anchor="ls")
    
    draw.text(
        (x_date, y_date_base + 55),
        conf['date_nat_txt'], 
        font=font_date_nat, 
        fill="black", 
        anchor="ls",
        stroke_width=conf.get('native_stroke_width', 0),
        stroke_fill="black"
    )

    # --- SAVE ---
    clean_name = student_name.replace(' ', '_')
    path_out = os.path.join(OUTPUT_DIR, f"certif_{language}_{clean_name}.png")
    
    img.save(path_out)
    print(f"✅ Généré : {path_out}")

if __name__ == "__main__":
    generate_certificate('cn', 'Yanis Sensei', 1)
    generate_certificate('kr', 'Mohamed Amine', 2)
    generate_certificate('jp', 'Sarah Connor', 3)