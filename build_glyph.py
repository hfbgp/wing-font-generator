# build_glyph.py
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from utils import get_glyph_name_by_char
import math

GLYPH_PREFIX = "wingfont"

def _get_relative_bounds(glyph_set, glyph_name, transform):
    """輔助函數：計算字形在應用變換（無 dx/dy）後的相對邊界"""
    bPen = BoundsPen(glyph_set)
    rel_transform = (transform[0], transform[1], transform[2], transform[3], 0, 0)
    
    if glyph_name in glyph_set:
        glyph_set[glyph_name].draw(TransformPen(bPen, rel_transform))
        bounds = bPen.bounds
        if bounds:
            return bounds[1], bounds[3] # (yMin, yMax)
    return 0, 0 

def _get_string_relative_bounds(font, glyph_set, glyph_order, text, scale, cos, sin, spacing_in_units=0):
    """輔助函數：計算字符串在縮放/旋轉後的相對邊界 (yMin, yMax)。"""
    bPen = BoundsPen(glyph_set)
    x_pos_rel, y_pos_rel = 0, 0
    
    for idx, char in enumerate(text):
        glyph_name = get_glyph_name_by_char(font, char)
        if isinstance(glyph_name, str) and glyph_name in glyph_set:
            transform_rel = (
                scale * cos,   # xx
                scale * sin,   # xy
                -scale * sin,  # yx
                scale * cos,   # yy
                x_pos_rel,     # dx
                y_pos_rel      # dy
            )
            glyph_set[glyph_name].draw(TransformPen(bPen, transform_rel))
            
            if glyph_name in glyph_order:
                advance_width_scaled = round(font['hmtx'][glyph_name][0] * scale)
                x_pos_rel += advance_width_scaled * cos
                y_pos_rel += advance_width_scaled * sin
                
                if idx < len(text) - 1:
                    spacing_x_component = (spacing_in_units * scale) * cos
                    spacing_y_component = (spacing_in_units * scale) * sin
                    x_pos_rel += spacing_x_component
                    y_pos_rel += spacing_y_component

    bounds = bPen.bounds
    if bounds:
        return bounds[1], bounds[3] 
    return 0, 0 

def generate_glyphs(
    base_font, anno_font, output_font, mapping, 
    anno_scale=0.35, base_scale=0.60, 
    anno_y_offset=0.70, base_y_offset=0.0,
    base_rotate=0.0, anno_rotate=0.0,
    min_lsb=None,
    invert=False,
    fit=False,
    fit_padding=0.03,
    anno_spacing=-0.03,
    auto_width=False,
    auto_height=False,
    top_padding_percent=None,
    bottom_padding_percent=None
):
    output_glyph_name_used = {}
    
    base_glyph_set = base_font.getGlyphSet()
    anno_glyph_set = anno_font.getGlyphSet()
    output_glyph_set = output_font.getGlyphSet()

    anno_glyph_order = anno_font.getGlyphOrder()
    base_glyph_order = base_font.getGlyphOrder()
    
    base_units_per_em = base_font['head'].unitsPerEm
    anno_units_per_em = anno_font['head'].unitsPerEm
    
    # 追蹤整套字體的最高點與最低點 (用於 auto_height)
    global_max_y = -99999
    global_min_y = 99999

    # --- 步驟 A: 計算原始偏移量 (單位) ---
    y_offset_anno_orig = round(base_units_per_em * anno_y_offset) 
    y_offset_base_orig = round(base_units_per_em * base_y_offset)
    
    # 字符間距 (單位)
    spacing_in_units = anno_units_per_em * anno_spacing

    if invert:
        print("[INFO] Inverting annotation and base glyph vertical positions.")
    if fit:
        print(f"[INFO] Horizontal fitting ENABLED with {fit_padding*100:.0f}% padding.")
    if auto_width:
        print(f"[INFO] Auto-width ENABLED: Base width will expand if annotation is too long.")
    if auto_height:
        print(f"[INFO] Auto-height ENABLED: Font vertical metrics will be adjusted if glyphs exceed bounds.")
    if anno_spacing != 0:
        print(f"[INFO] Spacing between annotation characters: {anno_spacing*100:.0f}%.")

    # --- 步驟 B: 計算旋轉和縮放矩陣 ---
    base_rad = math.radians(base_rotate)
    base_cos = math.cos(base_rad)
    base_sin = math.sin(base_rad)
    base_transform_rel = (base_scale * base_cos, base_scale * base_sin, -base_scale * base_sin, base_scale * base_cos, 0, 0)
    
    anno_rad = math.radians(anno_rotate)
    anno_cos = math.cos(anno_rad)
    anno_sin = math.sin(anno_rad)
    
    # --- 步驟 C: 建立可重複使用的 Pens ---
    base_bPen = BoundsPen(base_glyph_set) 
    anno_bPen = BoundsPen(anno_glyph_set) 
    
    # --- 步驟 D: 計算全局參考邊界 (Y 軸) ---
    REF_ANNO_STR = "kwaang3"
    GLOBAL_ANNO_BOTTOM_REL, GLOBAL_ANNO_TOP_REL = _get_string_relative_bounds(
        anno_font, anno_glyph_set, anno_glyph_order,
        REF_ANNO_STR,
        anno_scale, anno_cos, anno_sin,
        spacing_in_units
    )
    
    REF_BASE_CHAR = "逛" # U+905B
    ref_base_glyph_name = get_glyph_name_by_char(base_font, REF_BASE_CHAR)
    
    if not isinstance(ref_base_glyph_name, str) or ref_base_glyph_name not in base_glyph_set:
        REF_BASE_CHAR = "一" # U+4E00
        ref_base_glyph_name = get_glyph_name_by_char(base_font, REF_BASE_CHAR)
        if not isinstance(ref_base_glyph_name, str):
             print(f"[ERROR] Cannot find reference glyph. Using (0,0) bounds.")
             ref_base_glyph_name = None 
    
    print(f"[INFO] Global Refs: Anno='{REF_ANNO_STR}', Base='{REF_BASE_CHAR}'")
    GLOBAL_BASE_BOTTOM_REL, GLOBAL_BASE_TOP_REL = _get_relative_bounds(
        base_glyph_set, ref_base_glyph_name, base_transform_rel
    )

    # --- 步驟 E: 計算最終 DY 偏移量 ---
    anno_was_above = y_offset_anno_orig > y_offset_base_orig
    final_base_dy = y_offset_base_orig
    final_anno_dy = y_offset_anno_orig
    
    if invert:
        if anno_was_above:
            final_anno_dy = y_offset_base_orig + GLOBAL_BASE_BOTTOM_REL - GLOBAL_ANNO_BOTTOM_REL
            final_base_dy = y_offset_anno_orig + GLOBAL_ANNO_TOP_REL - GLOBAL_BASE_TOP_REL
        else:
            final_anno_dy = y_offset_base_orig + GLOBAL_BASE_TOP_REL - GLOBAL_ANNO_TOP_REL
            final_base_dy = y_offset_anno_orig + GLOBAL_ANNO_BOTTOM_REL - GLOBAL_BASE_BOTTOM_REL
    
    final_unannotated_dy = final_base_dy

    # --- 第一部分：處理有註音的字形 ---
    processed_chars = set(mapping.keys())
    processed_glyph_names = set() 
    cnt = 0
    
    for base_char, anno_strs_dict in mapping.items():
        glyph_name_raw = get_glyph_name_by_char(base_font, base_char)
        if not isinstance(glyph_name_raw, str) or glyph_name_raw not in base_glyph_order:
            continue
        glyph_name = glyph_name_raw
        processed_glyph_names.add(glyph_name) 
        if glyph_name not in base_glyph_set:
            continue
            
        original_base_width = base_font['hmtx'][glyph_name][0]
        
        # 步驟 1: 計算基礎字形原始視覺中心 (僅用於 X 軸)
        base_bPen.bounds = None 
        base_glyph_set[glyph_name].draw(base_bPen)
        glyph_bounds = base_bPen.bounds
        if glyph_bounds is None: 
            x_visual_center_orig = original_base_width / 2
            y_visual_center_orig = 0
        else:
            x_visual_center_orig = (glyph_bounds[0] + glyph_bounds[2]) / 2
            y_visual_center_orig = (glyph_bounds[1] + glyph_bounds[3]) / 2

        for i, anno_str in enumerate(anno_strs_dict.keys()):
            if i == 0:
                new_glyph_name = glyph_name
            else:
                new_glyph_name = GLYPH_PREFIX+str(cnt).zfill(6)
            while new_glyph_name in output_glyph_name_used or (i > 0 and new_glyph_name == glyph_name):
                new_glyph_name = GLYPH_PREFIX+str(cnt).zfill(6)
                cnt += 1
            
            # --- Pass 1: 測量註音寬度 ---
            anno_bPen.bounds = None
            x_pos_rel_local, y_pos_rel_local = 0, 0
            
            # 模擬繪製以計算寬度
            for idx, char in enumerate(anno_str):
                anno_glyph_name = get_glyph_name_by_char(anno_font, char)
                if isinstance(anno_glyph_name, str) and anno_glyph_name in anno_glyph_set:
                    transform_rel_local = (
                        anno_scale * anno_cos, anno_scale * anno_sin,
                        -anno_scale * anno_sin, anno_scale * anno_cos,
                        x_pos_rel_local, y_pos_rel_local
                    )
                    anno_glyph_set[anno_glyph_name].draw(TransformPen(anno_bPen, transform_rel_local))
                    
                    if anno_glyph_name in anno_glyph_order:
                        advance_width_scaled = round(anno_font['hmtx'][anno_glyph_name][0] * anno_scale)
                        x_pos_rel_local += advance_width_scaled * anno_cos
                        y_pos_rel_local += advance_width_scaled * anno_sin
                        if idx < len(anno_str) - 1:
                            x_pos_rel_local += (spacing_in_units * anno_scale) * anno_cos
                            y_pos_rel_local += (spacing_in_units * anno_scale) * anno_sin

            anno_bounds_rel_local = anno_bPen.bounds 
            anno_visual_width = 0
            x_visual_center_anno_rel = 0
            if anno_bounds_rel_local:
                anno_visual_width = anno_bounds_rel_local[2] - anno_bounds_rel_local[0]
                x_visual_center_anno_rel = (anno_bounds_rel_local[0] + anno_bounds_rel_local[2]) / 2.0

            # --- 決定最終容器寬度 ---
            final_advance_width = original_base_width
            safe_width_factor = (1.0 - fit_padding)
            if safe_width_factor <= 0: safe_width_factor = 1.0
            
            if auto_width and (anno_visual_width > original_base_width * safe_width_factor):
                final_advance_width = math.ceil(anno_visual_width / safe_width_factor)

            target_center_x = final_advance_width / 2

            pen = TTGlyphPen(output_glyph_set)
            composite_bPen = BoundsPen(output_glyph_set)
            
            # --- Pass 2: 繪製基礎字形 (居中) ---
            x_transformed_center = (
                x_visual_center_orig * (base_scale * base_cos) + 
                y_visual_center_orig * (-base_scale * base_sin)
            )
            x_offset_base = target_center_x - x_transformed_center
            
            base_transform = (
                base_transform_rel[0], base_transform_rel[1], 
                base_transform_rel[2], base_transform_rel[3],
                x_offset_base,           
                final_base_dy            
            )
            if glyph_bounds is not None:
                base_glyph_set[glyph_name].draw(TransformPen(pen, base_transform))
                base_glyph_set[glyph_name].draw(TransformPen(composite_bPen, base_transform))
            
            # --- Pass 3: 繪製註音 (居中，可能壓縮) ---
            x_compression_ratio = 1.0 
            current_anno_scale_x = anno_scale
            current_anno_scale_y = anno_scale
            
            safe_anno_width = final_advance_width * safe_width_factor
            
            if fit and (anno_visual_width > safe_anno_width):
                if safe_anno_width <= 0: safe_anno_width = anno_visual_width
                x_compression_ratio = safe_anno_width / anno_visual_width 
                current_anno_scale_x = anno_scale * x_compression_ratio
            
            final_anno_xx = current_anno_scale_x * anno_cos
            final_anno_xy = current_anno_scale_x * anno_sin
            final_anno_yx = -current_anno_scale_y * anno_sin
            final_anno_yy = current_anno_scale_y * anno_cos
            
            x_visual_center_anno_compressed = x_visual_center_anno_rel * x_compression_ratio
            x_start = target_center_x - x_visual_center_anno_compressed
            y_start = final_anno_dy 
            
            x_position = x_start
            y_position = y_start
            
            for idx, char in enumerate(anno_str):
                anno_glyph_name = get_glyph_name_by_char(anno_font, char)
                if isinstance(anno_glyph_name, str) and anno_glyph_name in anno_glyph_set:
                    transform = (
                        final_anno_xx, final_anno_xy, 
                        final_anno_yx, final_anno_yy,
                        x_position, y_position
                    )
                    
                    anno_glyph_set[anno_glyph_name].draw(TransformPen(pen, transform))
                    anno_glyph_set[anno_glyph_name].draw(TransformPen(composite_bPen, transform))
                    
                    if anno_glyph_name in anno_glyph_order:
                        advance_width_scaled = round(anno_font['hmtx'][anno_glyph_name][0] * anno_scale)
                        x_position += (advance_width_scaled * x_compression_ratio) * anno_cos
                        y_position += (advance_width_scaled * x_compression_ratio) * anno_sin
                        
                        if idx < len(anno_str) - 1:
                            x_position += (spacing_in_units * current_anno_scale_x) * anno_cos
                            y_position += (spacing_in_units * current_anno_scale_x) * anno_sin

            # --- [Auto-Height] 追蹤邊界 ---
            if auto_height:
                final_bounds = composite_bPen.bounds
                if final_bounds:
                    # (xMin, yMin, xMax, yMax)
                    if final_bounds[1] < global_min_y: global_min_y = final_bounds[1]
                    if final_bounds[3] > global_max_y: global_max_y = final_bounds[3]

            if 'vmtx' in output_font.keys():
                if glyph_name in base_glyph_order: 
                    output_font['vmtx'][new_glyph_name] = base_font['vmtx'][glyph_name]
            
            if 'hmtx' in output_font:
                final_bounds = composite_bPen.bounds
                calculated_lsb = final_bounds[0] if final_bounds else 0.0
                
                if min_lsb is not None:
                    final_lsb = round(max(min_lsb, calculated_lsb))
                else:
                    final_lsb = round(calculated_lsb) 
                
                output_font['hmtx'][new_glyph_name] = (int(final_advance_width), final_lsb)
                
            output_font['glyf'][new_glyph_name] = pen.glyph()
            output_glyph_name_used[new_glyph_name] = True
            mapping[base_char][anno_str] = (new_glyph_name, i)
            if i == 0:
                output_font.getBestCmap()[ord(base_char)] = new_glyph_name

    # --- 第二部分：處理沒有註音的字形 ---
    print("\nProcessing un-annotated glyphs...")
    print("="*40)
            
    skipped_no_outline = []
    
    for glyph_name in base_glyph_order:
        if glyph_name in processed_glyph_names:
            continue

        if glyph_name not in base_glyph_set:
            skipped_no_outline.append(glyph_name)
            continue
        
        base_advance_width, base_lsb = base_font['hmtx'][glyph_name]
        target_center_x = base_advance_width / 2
        
        pen = TTGlyphPen(output_glyph_set)
        composite_bPen = BoundsPen(output_glyph_set)
        
        base_bPen.bounds = None 
        base_glyph_set[glyph_name].draw(base_bPen)
        glyph_bounds = base_bPen.bounds
        
        if glyph_bounds is None: 
            x_visual_center_orig = base_advance_width / 2
            y_visual_center_orig = 0
        else:
            x_visual_center_orig = (glyph_bounds[0] + glyph_bounds[2]) / 2
            y_visual_center_orig = (glyph_bounds[1] + glyph_bounds[3]) / 2
        
        x_transformed_center = (
            x_visual_center_orig * (base_scale * base_cos) + 
            y_visual_center_orig * (-base_scale * base_sin)
        )
        x_offset = target_center_x - x_transformed_center
        
        transform = (
            base_transform_rel[0], base_transform_rel[1],
            base_transform_rel[2], base_transform_rel[3],
            x_offset,                  
            final_unannotated_dy       
        )
        
        if glyph_bounds is not None:
            base_glyph_set[glyph_name].draw(TransformPen(pen, transform))
            base_glyph_set[glyph_name].draw(TransformPen(composite_bPen, transform))
        
        # --- [Auto-Height] 追蹤邊界 ---
        if auto_height:
            final_bounds = composite_bPen.bounds
            if final_bounds:
                if final_bounds[1] < global_min_y: global_min_y = final_bounds[1]
                if final_bounds[3] > global_max_y: global_max_y = final_bounds[3]

        output_font['glyf'][glyph_name] = pen.glyph()
        
        final_bounds = composite_bPen.bounds
        calculated_lsb = final_bounds[0] if final_bounds else 0.0
        
        if min_lsb is not None:
            final_lsb = round(max(min_lsb, calculated_lsb))
        else:
            final_lsb = round(calculated_lsb)
            
        output_font['hmtx'][glyph_name] = (base_advance_width, final_lsb)
    
    if skipped_no_outline:
        print(f"\n[INFO] Skipped {len(skipped_no_outline)} empty glyphs.")

    # --- [Auto-Height] 應用全局垂直度量調整 ---
    # --- [Custom Auto-Height with CLI padding control] ---
    if auto_height and global_max_y != -99999:

        hhea = output_font['hhea']
        os2  = output_font['OS/2']
        upm  = output_font['head'].unitsPerEm

        # --- 若 CLI 有輸入 -tp / -bp，則完全以使用者指定為主 ---
        if top_padding_percent is not None and bottom_padding_percent is not None:
            tp = top_padding_percent
            bp = bottom_padding_percent
        else:
            # --- 否則使用你原本指定的邏輯（含 invert） ---
            if invert:
                tp = -0.60   # invert 時，上留白 -60%
                bp =  0.10   # invert 時，下留白 10%
            else:
                tp =  0.10   # 默认 上留白 10%
                bp = -0.60   # 默认 下留白 -60%

        # 轉成 units
        top_padding  = int(upm * tp)
        bottom_pad   = int(upm * bp)

        # 真實字形的上下邊界
        glyph_top    = round(global_max_y)
        glyph_bottom = round(global_min_y)

        # 設定 font metrics
        new_ascent  = glyph_top + top_padding
        new_descent = glyph_bottom - bottom_pad  # 注意：descent 是負值

        # 寫入 hhea
        hhea.ascent  = new_ascent
        hhea.descent = new_descent

        # 寫入 OS/2
        os2.sTypoAscender  = new_ascent
        os2.sTypoDescender = new_descent
        os2.usWinAscent    = new_ascent
        os2.usWinDescent   = abs(new_descent)

        print(f"[Auto-Height] top={tp*100:.1f}%, bottom={bp*100:.1f}%")

    print("\nDone scaling un-annotated glyphs.")