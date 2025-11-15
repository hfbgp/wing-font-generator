# wing-font.py

from fontTools.ttLib import TTFont
from mappings.csv_parser import load_mapping
from chain_context_handler import buildChainSub
from liga_handler import buildLiga
from build_glyph import generate_glyphs
import sys
import argparse
from fontTools import subset
from functools import reduce
from utils import get_glyph_name_by_char
import operator
import string 

# ... (語言 ID 常量) ...
WINDOWS_ENGLISH_IDS = (3, 1, 0x0409) 
MAC_ROMAN_IDS = (1, 0, 0)          
WINDOWS_CHINESE_SIMPLIFIED_IDS = (3, 1, 0x0804) 
WINDOWS_CHINESE_TAIWAN_IDS = (3, 1, 0x0404)     
WINDOWS_CHINESE_HONGKONG_IDS = (3, 1, 0x0C04)   

def set_family_names(font, name_map):
    table = font["name"]
    name_ids = (1, 4, 6, 16) 
    
    for (plat_id, enc_id, lang_id), new_family_name in name_map.items():
        if new_family_name is None:
            continue
            
        for name_id in name_ids:
            old_name_rec = table.getName(
                nameID=name_id,
                platformID=plat_id,
                platEncID=enc_id,
                langID=lang_id,
            )
            
            lang_str = f"P:{plat_id}/E:{enc_id}/L:{hex(lang_id)}"
            old_name = old_name_rec.toUnicode() if old_name_rec else "N/A"
            print(f"[{lang_str}] Changing NameID {name_id} from '{old_name}' to '{new_family_name}'")

            table.setName(
                new_family_name,
                nameID=name_id,
                platformID=plat_id,
                platEncID=enc_id,
                langID=lang_id,
            )


def main(
    base_font_file, 
    anno_font_file, 
    output_prefix, 
    mapping, 
    en_name=None,
    cn_name=None,
    tw_name=None,
    hk_name=None,
    base_scale=0.60,
    anno_scale=0.35,
    anno_y_offset=0.70,
    base_y_offset=0.0,
    base_rotate=0.0,
    anno_rotate=0.0,
    min_lsb=None,
    optimize=False,
    clear_layout=False,
    invert=False,
    fit=False,
    fit_padding=0.03,
    anno_spacing=-0.03,
    auto_width=False,
    auto_height=False,
    top_padding_percent=None,
    bottom_padding_percent=None
):
    # Load the fonts and mapping
    base_font = TTFont(base_font_file)
    anno_font = TTFont(anno_font_file)
    output_font = TTFont(base_font_file)
    word_mapping, char_mapping = load_mapping(base_font, mapping)

    # 創建名稱映射字典
    name_map = {}
    
    if en_name is not None:
        name_map[WINDOWS_ENGLISH_IDS] = en_name
        name_map[MAC_ROMAN_IDS] = en_name 
    if cn_name is not None:
        name_map[WINDOWS_CHINESE_SIMPLIFIED_IDS] = cn_name
    if tw_name is not None:
        name_map[WINDOWS_CHINESE_TAIWAN_IDS] = tw_name
    if hk_name is not None:
        name_map[WINDOWS_CHINESE_HONGKONG_IDS] = hk_name
    
    if name_map:
        set_family_names(output_font, name_map)

    # Combine the glyphs and save the new font
    generate_glyphs(
        base_font, 
        anno_font, 
        output_font, 
        char_mapping, 
        base_scale=base_scale, 
        anno_scale=anno_scale, 
        anno_y_offset=anno_y_offset,
        base_y_offset=base_y_offset,
        base_rotate=base_rotate,
        anno_rotate=anno_rotate,
        min_lsb=min_lsb,
        invert=invert,
        fit=fit,
        fit_padding=fit_padding,
        anno_spacing=anno_spacing,
        auto_width=auto_width,
        auto_height=auto_height,
        top_padding_percent=top_padding_percent,
        bottom_padding_percent=bottom_padding_percent
    )

    # Build Chain Contextual Substitution
    buildChainSub(output_font, word_mapping, char_mapping)
    
    # Replace glyph by new glyph using liga
    buildLiga(output_font, char_mapping)

    # if size optimization is required
    if optimize:
        print("Optimizing font size by subsetting...")
        glyphs_to_be_kept = [get_glyph_name_by_char(base_font, str(i)) for i in range(0, 10)]
        
        for value in char_mapping.values():
            for glyph_name, idx in value.values():
                glyphs_to_be_kept.append(glyph_name)
        
        chars_to_keep_additionally = string.punctuation + string.ascii_letters + '丅，。！？《》（）「」『』｛｝〖〗【】［］、……——＠＃￥％＆＊+-/“”：；‘’／０１２３４５６７８９ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ'

        print(f"Keeping additional {len(chars_to_keep_additionally)} punctuation and letter glyphs...")
        for char in chars_to_keep_additionally:
            glyph_name = get_glyph_name_by_char(base_font, char)
            if glyph_name:
                glyphs_to_be_kept.append(glyph_name)
        
        options = subset.Options()
        
        if clear_layout:
            print("WARNING: Clearing layout features to resolve potential FeatureParams error.")
            options.layout_features = [] 
        
        subsetter = subset.Subsetter(options=options)
        
        valid_glyphs_to_keep = list(set(g for g in glyphs_to_be_kept if g is not None))
        print(f"Total unique glyphs to keep: {len(valid_glyphs_to_keep)}")
        
        subsetter.populate(glyphs=valid_glyphs_to_keep)
        subsetter.subset(output_font)

    # Save the new font
    output_font.save(str(output_prefix)+".ttf")
    print(f"New font saved as {output_prefix}.ttf")
    output_font.flavor = 'woff'
    output_font.save(str(output_prefix+".woff"))
    print(f"New font saved as {output_prefix}.woff")
    
    base_font.close()
    anno_font.close()
    output_font.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument('-i', '--base-font-file', help="Base font in .ttf fomrat", required=True)
    parser.add_argument('-a', '--anno-font_file', help="Annotation font in .ttf fomrat", required=True)
    parser.add_argument('-o', '--output-prefix', help="Output prefix for .ttf and .woff file", required=True)
    parser.add_argument('-m', '--mapping', help="CSV file for the mapping between base font and annotation font", required=True)
    parser.add_argument('-ay', '--anno-y-offset', type=float, default=0.7, help="Y offset in (percentage) for annotation string")
    parser.add_argument('-by', '--base-y-offset', type=float, default=0.0, help="Y offset in (percentage) for base font string (default: 0.0)")
    parser.add_argument('-bs', '--base-scale', type=float, default=0.60, help="The scaling factor for the base font")
    parser.add_argument('-as', '--anno-scale', type=float, default=0.35, help="The scaling factor for the base font")
    parser.add_argument('-br', '--base-rotate', type=float, default=0.0, help="Rotation (in degrees) for the base font glyph (default: 0.0)")
    parser.add_argument('-ar', '--anno-rotate', type=float, default=0.0, help="Rotation (in degrees) for the annotation string (default: 0.0)")
    parser.add_argument('-lsb', '--min-lsb', type=int, default=None, help="Force minimum LSB value (e.g., 0). If not set, LSB can be negative. (default: None)")
    parser.add_argument('-v', '--invert', action='store_true', help='Invert the annotation and base glyph')
    parser.add_argument('-fi', '--fit', action='store_true', help='Horizontally compress long annotations to fit within the glyph width.')
    parser.add_argument('-fp', '--fit-padding', type=float, default=0.03, help='Padding (percentage) for -fit. Compresses anno if width > advance_width * (1.0 - padding). (default: 0.03)')
    parser.add_argument('-asp', '--anno-spacing', type=float, default=-0.03, help='Additional spacing (percentage of anno UPM) between annotation characters. (default: -0.03)')
    parser.add_argument('-aw', '--auto-width', action='store_true', help='Automatically expand base_advance_width if annotation is wider than the base glyph.')
    parser.add_argument('-ah', '--auto-height', action='store_true', help='Automatically extend font vertical metrics (Ascender/Descender) if glyphs exceed bounds.') # <--- [新增]
    parser.add_argument('-opt', '--optimize', action="store_true", help="Optimizing size by subsetting annotated glyph only")
    parser.add_argument('-c', '--clear-layout', action="store_true", help="Clear existing OpenType layout features from the base font during optimization (to fix FeatureParams error).")
    parser.add_argument('-f', help="Replace with the new English family name")
    parser.add_argument('-fcn', help="Replace with the new Simplified Chinese family name (PRC)")
    parser.add_argument('-ftw', help="Replace with the new Traditional Chinese family name (Taiwan)")
    parser.add_argument('-fhk', help="Replace with the new Traditional Chinese family name (Hongkong)")
    parser.add_argument('-tp', '--top-padding', type=float, default=None, help="Top padding percentage (e.g., 0.1, -0.60). Overrides auto-height default behavior.")
    parser.add_argument('-bp', '--bottom-padding', type=float, default=None, help="Bottom padding percentage (e.g., -0.60, 0.1). Overrides auto-height default behavior.")

    try:
        options = parser.parse_args()
    except:
        parser.print_help()
        exit()
    main(
        base_font_file = options.base_font_file, 
        anno_font_file = options.anno_font_file, 
        output_prefix = options.output_prefix, 
        mapping = options.mapping,
        base_scale=options.base_scale,
        anno_scale=options.anno_scale,
        anno_y_offset=options.anno_y_offset,
        base_y_offset=options.base_y_offset,
        base_rotate=options.base_rotate,
        anno_rotate=options.anno_rotate,
        min_lsb=options.min_lsb,
        optimize=options.optimize,
        clear_layout=options.clear_layout,
        en_name = options.f, 
        cn_name = options.fcn, 
        tw_name = options.ftw,
        hk_name = options.fhk,
        invert = options.invert,
        fit = options.fit,
        fit_padding = options.fit_padding,
        anno_spacing = options.anno_spacing,
        auto_width = options.auto_width,
        auto_height = options.auto_height,
        top_padding_percent=options.top_padding,
        bottom_padding_percent=options.bottom_padding
    )