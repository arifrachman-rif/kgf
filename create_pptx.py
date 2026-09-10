import os
import sys
from PIL import Image, ImageDraw, ImageFont
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_kgf_logo():
    """Generates a high-resolution full-color logo image for PT Klumbayan Gold Farm"""
    img_size = (800, 800)
    image = Image.new("RGBA", img_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Outer Rounded Shield Card Background
    shape_bg = (24, 42, 32, 255) # Dark emerald surface
    border_col = (37, 64, 48, 255)
    draw.rounded_rectangle([20, 20, 780, 780], radius=80, fill=shape_bg, outline=border_col, width=12)
    
    # Shield Path Gold Outline
    shield_pts = [
        (400, 120), (620, 180), (620, 380),
        (400, 680),
        (180, 380), (180, 180)
    ]
    draw.polygon(shield_pts, fill=(229, 169, 60, 40), outline=(229, 169, 60, 255), width=10)
    
    # Sprout Center Icon
    # Stem
    draw.line([(400, 600), (400, 320)], fill=(229, 169, 60, 255), width=18)
    
    # Left Leaf
    draw.arc([220, 260, 400, 480], start=180, end=360, fill=(244, 196, 107, 255), width=16)
    # Right Leaf
    draw.arc([400, 260, 580, 480], start=180, end=360, fill=(229, 169, 60, 255), width=16)
    
    logo_path = "kgf_logo_fullcolor.png"
    image.save(logo_path, "PNG")
    return logo_path

def build_presentation():
    logo_path = create_kgf_logo()
    prs = Presentation()
    
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    blank_layout = prs.slide_layouts[6] # Blank layout
    
    # Colors
    C_DARK_BG = RGBColor(11, 19, 14)       # #0B130E
    C_DARK_CARD = RGBColor(18, 31, 23)     # #121F17
    C_DARK_BORDER = RGBColor(37, 64, 48)   # #254030
    
    C_LIGHT_BG = RGBColor(247, 249, 248)   # #F7F9F8
    C_LIGHT_CARD = RGBColor(255, 255, 255) # #FFFFFF
    C_LIGHT_BORDER = RGBColor(220, 230, 224)# #DCE6E0
    
    C_TEXT_DARK_SLIDE = RGBColor(242, 247, 244) # #F2F7F4
    C_TEXT_MUTED_DARK = RGBColor(155, 176, 163)# #9BB0A3
    
    C_TEXT_LIGHT_SLIDE = RGBColor(20, 35, 26)   # #14231A
    C_TEXT_MUTED_LIGHT = RGBColor(90, 110, 98) # #5A6E62
    
    C_GOLD = RGBColor(229, 169, 60)         # #E5A93C
    C_EMERALD = RGBColor(46, 139, 87)       # #2E8B57
    C_PLACEHOLDER_BG = RGBColor(232, 238, 234) # #E8EEEA
    C_PLACEHOLDER_BORDER = RGBColor(180, 200, 188)
    
    # Helper to add full-color header logo badge
    def add_header_logo(slide, is_dark=False):
        # Logo Image
        slide.shapes.add_picture(logo_path, Inches(0.6), Inches(0.4), Inches(0.6), Inches(0.6))
        
        # Logo Text Label
        tx_box = slide.shapes.add_textbox(Inches(1.3), Inches(0.38), Inches(4), Inches(0.7))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = "PT KLUMBAYAN GOLD FARM"
        p1.font.size = Pt(13)
        p1.font.bold = True
        p1.font.color.rgb = C_GOLD if is_dark else C_TEXT_LIGHT_SLIDE
        
        p2 = tf.add_paragraph()
        p2.text = "Regenerative Agribusiness & Traceability"
        p2.font.size = Pt(9)
        p2.font.color.rgb = C_TEXT_MUTED_DARK if is_dark else C_TEXT_MUTED_LIGHT

    # Helper to create photo placeholders
    def add_photo_placeholder(slide, left, top, width, height, label_text="[ SLOT FOTO / GAMBAR ]"):
        # Shape rectangle
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = C_PLACEHOLDER_BG
        shape.line.color.rgb = C_PLACEHOLDER_BORDER
        shape.line.width = Pt(1.5)
        
        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"📷 {label_text}\n(Klik kanan / Replace dengan foto lo)"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = C_TEXT_MUTED_LIGHT
        return shape

    # =========================================================================
    # SLIDE 1: COVER / TITLE SLIDE (Dark Theme)
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_layout)
    # Dark Background
    bg1 = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_DARK_BG
    bg1.line.color.rgb = C_DARK_BG
    
    add_header_logo(slide1, is_dark=True)
    
    # Left Content
    tx1 = slide1.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.5), Inches(4.8))
    tf1 = tx1.text_frame
    tf1.word_wrap = True
    
    p = tf1.paragraphs[0]
    p.text = "COMPANY PROFILE"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_GOLD
    p.space_after = Pt(12)
    
    p = tf1.add_paragraph()
    p.text = "PT Klumbayan Gold Farm"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_DARK_SLIDE
    p.space_after = Pt(8)
    
    p = tf1.add_paragraph()
    p.text = "Tech-Enabled Trading & Regenerative Agribusiness"
    p.font.size = Pt(20)
    p.font.color.rgb = C_TEXT_MUTED_DARK
    p.space_after = Pt(20)
    
    p = tf1.add_paragraph()
    p.text = "Membangun ekosistem agribisnis ramah lingkungan, terpercaya, dan terintegrasi dari petani lokal hingga pasar ekspor global."
    p.font.size = Pt(14)
    p.font.color.rgb = C_TEXT_DARK_SLIDE
    
    # Right Main Hero Photo Placeholder
    add_photo_placeholder(slide1, Inches(7.6), Inches(1.5), Inches(5.0), Inches(5.2), "[ SLOT FOTO UTAMA COVER / HERO IMAGE KGF ]")

    # =========================================================================
    # SLIDE 2: ABOUT US & OVERVIEW (Light Theme)
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_layout)
    bg2 = slide2.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg2.fill.solid()
    bg2.fill.fore_color.rgb = C_LIGHT_BG
    bg2.line.color.rgb = C_LIGHT_BG
    
    add_header_logo(slide2, is_dark=False)
    
    # Section Title
    tx2_t = slide2.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(1.0))
    tf2_t = tx2_t.text_frame
    p = tf2_t.paragraphs[0]
    p.text = "TENTANG KGF | Company Overview"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_LIGHT_SLIDE
    
    p = tf2_t.add_paragraph()
    p.text = "Integrasi Wanatani Berkelanjutan & Ekosistem Perdagangan Modern"
    p.font.size = Pt(15)
    p.font.color.rgb = C_TEXT_MUTED_LIGHT
    
    # Left Bullet Card
    card2 = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.2), Inches(6.2), Inches(4.7))
    card2.fill.solid()
    card2.fill.fore_color.rgb = C_LIGHT_CARD
    card2.line.color.rgb = C_LIGHT_BORDER
    
    tf2 = card2.text_frame
    tf2.word_wrap = True
    
    bullets2 = [
        ("Tahun Berdiri & Lokasi", "Didirikan pada tahun 2022 di Bandar Lampung, Indonesia dengan visi pemulihan lingkungan dan kemitraan petani."),
        ("Agregator & Trading House", "Mengelola pengolahan fisik pascapanen di Gudang Natar (Kapasitas 2.000 Ton), penjaminan mutu, dan logistik ekspor."),
        ("Jaringan Petani Mitra", "Mendampingi 1.250+ petani wanatani kopi, lada hitam, dan kakao di Lampung dan Sumatra."),
        ("Kredibilitas Internasional", "Implementator lokal utama proyek konsorsium aGROWforests (didanai GIZ) bersama mitra Eropa (Verstegen & Fairfood).")
    ]
    
    for idx, (title, desc) in enumerate(bullets2):
        p = tf2.paragraphs[0] if idx == 0 else tf2.add_paragraph()
        p.text = f"•  {title}"
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = C_EMERALD
        
        p_sub = tf2.add_paragraph()
        p_sub.text = f"    {desc}"
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = C_TEXT_LIGHT_SLIDE
        p_sub.space_after = Pt(12)

    # Right Photo Placeholder
    add_photo_placeholder(slide2, Inches(7.3), Inches(2.2), Inches(5.2), Inches(4.7), "[ SLOT FOTO 1: Gudang Natar / Fasilitas KGF ]")

    # =========================================================================
    # SLIDE 3: CORE COMMODITIES (Light Theme)
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_layout)
    bg3 = slide3.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg3.fill.solid()
    bg3.fill.fore_color.rgb = C_LIGHT_BG
    bg3.line.color.rgb = C_LIGHT_BG
    
    add_header_logo(slide3, is_dark=False)
    
    tx3_t = slide3.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.9))
    tf3_t = tx3_t.text_frame
    p = tf3_t.paragraphs[0]
    p.text = "KOMODITAS UNGGULAN | Core Products"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_LIGHT_SLIDE
    
    # 3 Product Cards
    prods = [
        ("Lada Hitam Lampung", "ASTA Grade 550 Premium", "Kualitas FAQ ekspor dengan berat jenis ≥580 g/l, jaminan ketertelusuran penuh & bebas pestisida."),
        ("Kopi Robusta Tanggamus", "Sorted Grade 1 Green Beans", "Kopi Robusta petik merah pilihan (defect 80/120) untuk pasar eksportir multinasional & industri kopi."),
        ("Kakao Olahan", "Downstream Cocoa Products", "Pengolahan pascapanen kakao komunitas menjadi produk kakao olahan (nibs & powder) berkualitas tinggi.")
    ]
    
    for i, (p_title, p_sub, p_desc) in enumerate(prods):
        left_pos = Inches(0.8 + i * 3.9)
        c = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(2.1), Inches(3.7), Inches(2.8))
        c.fill.solid()
        c.fill.fore_color.rgb = C_LIGHT_CARD
        c.line.color.rgb = C_LIGHT_BORDER
        
        tf = c.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = p_title
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = C_EMERALD
        p.space_after = Pt(4)
        
        p = tf.add_paragraph()
        p.text = p_sub
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = C_GOLD
        p.space_after = Pt(10)
        
        p = tf.add_paragraph()
        p.text = p_desc
        p.font.size = Pt(12)
        p.font.color.rgb = C_TEXT_MUTED_LIGHT

    # Bottom Photo Placeholder
    add_photo_placeholder(slide3, Inches(0.8), Inches(5.1), Inches(11.733), Inches(1.9), "[ SLOT FOTO 2: Koleksi Produk Lada, Kopi & Kakao KGF ]")

    # =========================================================================
    # SLIDE 4: TECHNOLOGY & TRACEABILITY (Dark Theme)
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_layout)
    bg4 = slide4.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg4.fill.solid()
    bg4.fill.fore_color.rgb = C_DARK_BG
    bg4.line.color.rgb = C_DARK_BG
    
    add_header_logo(slide4, is_dark=True)
    
    tx4_t = slide4.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.9))
    tf4_t = tx4_t.text_frame
    p = tf4_t.paragraphs[0]
    p.text = "TEKNOLOGI & KETERTELUSURAN | TAPAK ERP System"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_DARK_SLIDE
    
    # Left Tech Card
    c4 = slide4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.2), Inches(6.2), Inches(4.7))
    c4.fill.solid()
    c4.fill.fore_color.rgb = C_DARK_CARD
    c4.line.color.rgb = C_DARK_BORDER
    
    tf4 = c4.text_frame
    tf4.word_wrap = True
    
    tech_items = [
        ("Aplikasi TAPAK", "Sistem ERP berbasis Event-Sourcing (Lot & Log Graph Model) untuk mencatat transaksi dan ketertelusuran komoditas."),
        ("Validasi Standar EUDR", "Pemetaan polygon GPS 5.000+ kebun petani untuk membuktikan produk 100% deforestation-free sesuai regulasi Uni Eropa."),
        ("AI-CCDSS & AgriMEL", "Kecerdasan buatan untuk pemantauan iklim serta aplikasi mobile pengumpulan data lapangan secara offline-first.")
    ]
    
    for idx, (t_name, t_desc) in enumerate(tech_items):
        p = tf4.paragraphs[0] if idx == 0 else tf4.add_paragraph()
        p.text = f"✓  {t_name}"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = C_GOLD
        
        p_sub = tf4.add_paragraph()
        p_sub.text = f"    {t_desc}"
        p_sub.font.size = Pt(13)
        p_sub.font.color.rgb = C_TEXT_DARK_SLIDE
        p_sub.space_after = Pt(16)

    # Right Photo / Screenshot Placeholder
    add_photo_placeholder(slide4, Inches(7.3), Inches(2.2), Inches(5.2), Inches(4.7), "[ SLOT FOTO 3: Screenshot Aplikasi TAPAK / Peta Polygon ]")

    # =========================================================================
    # SLIDE 5: CONSORTIUM & PARTNERS (Light Theme)
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_layout)
    bg5 = slide5.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg5.fill.solid()
    bg5.fill.fore_color.rgb = C_LIGHT_BG
    bg5.line.color.rgb = C_LIGHT_BG
    
    add_header_logo(slide5, is_dark=False)
    
    tx5_t = slide5.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.9))
    tf5_t = tx5_t.text_frame
    p = tf5_t.paragraphs[0]
    p.text = "KEMITRAAN & PASAR EKSPOR | Strategic Consortium"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_LIGHT_SLIDE
    
    # 4 Partner Cards
    partners = [
        ("Verstegen (Belanda)", "Buyer Utama Rempah", "Offtaker lada hitam ekspor dengan komitmen 100% rantai pasok bebas deforestasi."),
        ("Fairfood (Belanda)", "Mitra Teknologi NGO", "Penyedia Traceapp untuk transparansi rantai pasok & insentif petani berbasis blockchain."),
        ("Eksportir Multinasional", "Olam / LDC / ECOM", "Jaringan pembeli komoditas kopi Robusta & lada untuk pasar ekspor global."),
        ("Dukungan Lembaga", "GIZ / EU / BAPPENAS", "Didukung proyek aGROWforests+ & diakui BAPPENAS dalam pengembangan wanatani.")
    ]
    
    for i, (part_n, part_r, part_d) in enumerate(partners):
        col = i % 2
        row = i // 2
        l_pos = Inches(0.8 + col * 3.3)
        t_pos = Inches(2.2 + row * 2.4)
        
        c = slide5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l_pos, t_pos, Inches(3.1), Inches(2.2))
        c.fill.solid()
        c.fill.fore_color.rgb = C_LIGHT_CARD
        c.line.color.rgb = C_LIGHT_BORDER
        
        tf = c.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = part_n
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = C_EMERALD
        
        p = tf.add_paragraph()
        p.text = part_r
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_GOLD
        p.space_after = Pt(6)
        
        p = tf.add_paragraph()
        p.text = part_d
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_MUTED_LIGHT

    # Right Photo Placeholder
    add_photo_placeholder(slide5, Inches(7.3), Inches(2.2), Inches(5.2), Inches(4.7), "[ SLOT FOTO 4: Dokumentasi Kemitraan / Pameran D-8 Halal Expo ]")

    # =========================================================================
    # SLIDE 6: SUSTAINABILITY & IMPACT (Light Theme)
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_layout)
    bg6 = slide6.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg6.fill.solid()
    bg6.fill.fore_color.rgb = C_LIGHT_BG
    bg6.line.color.rgb = C_LIGHT_BG
    
    add_header_logo(slide6, is_dark=False)
    
    tx6_t = slide6.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.9))
    tf6_t = tx6_t.text_frame
    p = tf6_t.paragraphs[0]
    p.text = "DAMPAK SOSIAL & LINGKUNGAN | Sustainability & Impact"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_LIGHT_SLIDE
    
    # 4 Impact Metric Boxes
    metrics = [
        ("1.250+", "Petani Wanatani Mitra", "Didampingi dalam praktik regeneratif & bibit unggul."),
        ("100%", "Kepatuhan EUDR", "Jaminan komoditas bebas deforestasi & terverifikasi."),
        ("+35%", "Kenaikan Pendapatan", "Melalui premi mutu & diversifikasi hasil kebun."),
        ("20%+", "Petani Wanita & Pemuda", "Prioritas pemberdayaan gender & regenerasi petani.")
    ]
    
    for i, (m_val, m_lbl, m_sub) in enumerate(metrics):
        left_pos = Inches(0.8 + i * 2.95)
        c = slide6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_pos, Inches(2.2), Inches(2.75), Inches(2.5))
        c.fill.solid()
        c.fill.fore_color.rgb = C_LIGHT_CARD
        c.line.color.rgb = C_LIGHT_BORDER
        
        tf = c.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = m_val
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = C_GOLD
        
        p = tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        p.text = m_lbl
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_EMERALD
        p.space_after = Pt(4)
        
        p = tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        p.text = m_sub
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_MUTED_LIGHT

    # Bottom Photo Placeholder
    add_photo_placeholder(slide6, Inches(0.8), Inches(4.9), Inches(11.733), Inches(2.0), "[ SLOT FOTO 5: Dokumentasi Pendampingan Petani di Lapangan ]")

    # =========================================================================
    # SLIDE 7: CONTACT & CLOSING (Dark Theme)
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_layout)
    bg7 = slide7.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg7.fill.solid()
    bg7.fill.fore_color.rgb = C_DARK_BG
    bg7.line.color.rgb = C_DARK_BG
    
    add_header_logo(slide7, is_dark=True)
    
    # Title
    tx7_t = slide7.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(6.5), Inches(1.2))
    tf7_t = tx7_t.text_frame
    p = tf7_t.paragraphs[0]
    p.text = "HUBUNGI KAMI | Contact Us"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_GOLD
    
    p = tf7_t.add_paragraph()
    p.text = "Mari Berkolaborasi Membangun Agribisnis Berkelanjutan"
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = C_TEXT_DARK_SLIDE
    
    # Left Contact Cards Grid
    contacts = [
        ("✉️  Email", "contact@klumbayangoldfarm.com\ninfo@agrowforests.id"),
        ("📞  No. Telepon / WhatsApp", "+62 811-7200-880 / +62 812-7900-1234"),
        ("🌐  Website", "www.klumbayangoldfarm.com\nwww.agrowforests.id"),
        ("📸  Instagram", "@klumbayangoldfarm"),
        ("💼  LinkedIn", "PT Klumbayan Gold Farm\n(linkedin.com/company/klumbayan-gold-farm)"),
        ("📍  Alamat Kantor & Gudang", "Bandar Lampung & Gudang Natar, Lampung, Indonesia")
    ]
    
    for i, (c_lbl, c_val) in enumerate(contacts):
        col = i % 2
        row = i // 2
        l_pos = Inches(0.8 + col * 3.3)
        t_pos = Inches(2.7 + row * 1.4)
        
        box = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l_pos, t_pos, Inches(3.1), Inches(1.25))
        box.fill.solid()
        box.fill.fore_color.rgb = C_DARK_CARD
        box.line.color.rgb = C_DARK_BORDER
        
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = c_lbl
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = C_GOLD
        
        p = tf.add_paragraph()
        p.text = c_val
        p.font.size = Pt(11)
        p.font.color.rgb = C_TEXT_DARK_SLIDE

    # Right Photo Placeholder
    add_photo_placeholder(slide7, Inches(7.6), Inches(1.5), Inches(5.0), Inches(5.3), "[ SLOT FOTO 6: Foto Tim KGF / Logo Besar Closing ]")

    # Save output
    output_filename = "KGF_Company_Profile.pptx"
    prs.save(output_filename)
    
    # Save a copy to Desktop
    desktop_dir = "C:/Users/rifra/Desktop"
    if os.path.exists(desktop_dir):
        prs.save(os.path.join(desktop_dir, output_filename))
        print(f"Saved copy to Desktop: {desktop_dir}/{output_filename}")
        
    print(f"Successfully generated presentation: {output_filename}")

if __name__ == "__main__":
    build_presentation()
