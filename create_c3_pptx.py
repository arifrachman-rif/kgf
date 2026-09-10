import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    
    # Optional: use 16:9
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    title_slide_layout = prs.slide_layouts[0]
    content_slide_layout = prs.slide_layouts[1]
    two_content_layout = prs.slide_layouts[3]
    blank_layout = prs.slide_layouts[6]

    # Helper function to add image placeholder shape
    def add_photo_placeholder(slide, left, top, width, height, text="[ PLACEHOLDER FOTO - KLIK KANAN > CHANGE PICTURE ]"):
        shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = pptx.dml.color.RGBColor(230, 230, 230)
        
        tf = shape.text_frame
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(14)
        p.font.color.rgb = pptx.dml.color.RGBColor(100, 100, 100)
        p.alignment = pptx.enum.text.PP_ALIGN.CENTER
        return shape

    # SLIDE 1: Title
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "aGROWforests+\nNature-Positive Agroforestry & Green Value Chains in Indonesia"
    subtitle.text = "EU SWITCH-Asia Programme — Call C3 Proposal\n\nLead Presenter: PT Klumbayan Gold Farm (KGF)\nTarget Regions: Lampung • Bangka Belitung • Aceh"
    
    # Add photo placeholder on cover
    add_photo_placeholder(slide, Inches(8.5), Inches(1), Inches(4), Inches(5), "[ FOTO COVER ]")

    # SLIDE 2: The Problem
    slide = prs.slides.add_slide(content_slide_layout)
    slide.shapes.title.text = "Systemic Threats to Indonesian Agribusiness"
    body = slide.placeholders[1].text_frame
    body.text = "Monoculture vulnerability, climate shocks & EU market exclusion risks."
    
    p = body.add_paragraph()
    p.text = "1. USD 2–3B Climate Losses: Annual economic losses for Sumatran smallholders due to deforestation-induced flooding, severe droughts, and soil erosion."
    
    p = body.add_paragraph()
    p.text = "2. Yield Degradation: Ageing tree stocks and monoculture soil exhaustion keep pepper, coffee, and cocoa farmers below living income thresholds."
    
    p = body.add_paragraph()
    p.text = "3. EUDR Compliance Deficit: Without geolocation polygons & verifiable MRV traceability, 5,000+ smallholders risk complete market exclusion from the EU."
    
    add_photo_placeholder(slide, Inches(8.5), Inches(2), Inches(4), Inches(4), "[ FOTO MASALAH / LINGKUNGAN ]")

    # SLIDE 3: Strategic Solution
    slide = prs.slides.add_slide(content_slide_layout)
    slide.shapes.title.text = "Integrated Solution Architecture"
    body = slide.placeholders[1].text_frame
    body.text = "Combining landscape stewardship, green value chains & innovative finance."
    
    p = body.add_paragraph()
    p.text = "1. Green Transformation: Transition 5,000 smallholders from monoculture to resilient agroforestry (Pepper, Coffee, Cocoa)."
    
    p = body.add_paragraph()
    p.text = "2. EUDR Traceability: Deploy TAPAK & Traceapp for farm-to-fork polygon mapping, ensuring 100% deforestation-free compliance."
    
    p = body.add_paragraph()
    p.text = "3. Landscape Finance: Establish a Landscape Finance Approach (LFA) mechanism to leverage EU grant funding with private capital."
    
    add_photo_placeholder(slide, Inches(8.5), Inches(2), Inches(4), Inches(4), "[ FOTO SOLUSI / PETANI ]")

    # SLIDE 4: Landscapes & Commodities
    slide = prs.slides.add_slide(two_content_layout)
    slide.shapes.title.text = "Three Strategic Commodity Hubs"
    
    left_body = slide.placeholders[1].text_frame
    left_body.text = "Lampung Hub (Black Pepper & Cocoa)"
    p = left_body.add_paragraph()
    p.text = "PT Klumbayan Gold Farm (KGF) operates Natar Processing Facility (2,000-ton capacity) and 1,250 registered farmers."
    
    p = left_body.add_paragraph()
    p.text = "Bangka Belitung Hub (White Pepper Agroforestry)"
    p1 = left_body.add_paragraph()
    p1.text = "PT CAN & Kelekak Demo Farm restoring post-mining soil and expanding community nurseries."
    
    p = left_body.add_paragraph()
    p.text = "Aceh Hub (Arabica Coffee)"
    p2 = left_body.add_paragraph()
    p2.text = "Sucafina Indonesia leading EUDR-compliant farm polygon mapping & quality enhancement in Central Aceh."
    
    add_photo_placeholder(slide, Inches(7), Inches(2.2), Inches(5.5), Inches(4.5), "[ FOTO PETA / LOKASI HUB ]")

    # SLIDE 5: Consortium Power
    slide = prs.slides.add_slide(content_slide_layout)
    slide.shapes.title.text = "World-Class Offtake & Tech Partners"
    body = slide.placeholders[1].text_frame
    body.text = "Bridging Indonesian farmers directly to European premium markets."
    
    p = body.add_paragraph()
    p.text = "• PT KGF (Lead Exporter & Operator): Tech-enabled agribusiness managing processing, TAPAK ERP, and farmer network."
    p = body.add_paragraph()
    p.text = "• Verstegen / VSS (Dutch Buyer Partner): Committed to 100% deforestation-free spice supply chain by Dec 2025."
    p = body.add_paragraph()
    p.text = "• Fairfood (Dutch Tech NGO): Developer of Traceapp blockchain transparency & farmer incentive reporting."
    p = body.add_paragraph()
    p.text = "• Sucafina & CAN (Supply Chain Partners): National B2B spice & coffee export integration across Bangka & Aceh."
    
    add_photo_placeholder(slide, Inches(9), Inches(2), Inches(3.5), Inches(4), "[ FOTO LOGO PARTNER ]")

    # SLIDE 6: Tech Engine (TAPAK)
    slide = prs.slides.add_slide(content_slide_layout)
    slide.shapes.title.text = "TAPAK: Event-Sourced Traceability"
    body = slide.placeholders[1].text_frame
    body.text = "Proprietary ERP system built by KGF for real-time EUDR validation."
    
    p = body.add_paragraph()
    p.text = "• Polygonal GPS mapping for 5,000 smallholder plots."
    p = body.add_paragraph()
    p.text = "• Event-sourcing graph architecture (Lot & Log tracking)."
    p = body.add_paragraph()
    p.text = "• AI Climate Decision Support (AI-CCDSS)."
    p = body.add_paragraph()
    p.text = "• Integrated AgriMEL app for offline field data collection."
    
    p = body.add_paragraph()
    p.text = "\nEUDR Readiness Guaranteed: Links every bag of Black Pepper, Coffee, and Cocoa directly to verified, non-deforested farmer plots."
    
    add_photo_placeholder(slide, Inches(8), Inches(2.5), Inches(4.5), Inches(3.5), "[ FOTO SCREENSHOT APLIKASI ]")

    # SLIDE 7: BAPPENAS Endorsement
    slide = prs.slides.add_slide(content_slide_layout)
    slide.shapes.title.text = "Aligned with National Priorities"
    body = slide.placeholders[1].text_frame
    body.text = "Formally endorsed by BAPPENAS & integrated into national planning."
    
    p = body.add_paragraph()
    p.text = "1. BAPPENAS Endorsed: Recognized at the Pepper Agroforestry Workshop as a benchmark public-private partnership model."
    p = body.add_paragraph()
    p.text = "2. FOLU Net Sink 2030: Agroforestry rehabilitation and verified MRV data contribute directly to national GHG reduction targets."
    p = body.add_paragraph()
    p.text = "3. RPJMN 2025–2029: Supports strategic commodity downstreaming and Indonesia's National Spice Downstreaming Roadmap."
    
    add_photo_placeholder(slide, Inches(8.5), Inches(2.5), Inches(4), Inches(3), "[ FOTO WORKSHOP / BAPPENAS ]")

    # SLIDE 8: Expected Impact & Metrics
    slide = prs.slides.add_slide(content_slide_layout)
    slide.shapes.title.text = "Target Key Performance Indicators"
    body = slide.placeholders[1].text_frame
    body.text = "Measurable Impact"
    
    p = body.add_paragraph()
    p.text = "• 5,000 Farmers Adopt Agroforestry: Across 6 target communities in Sumatra."
    p = body.add_paragraph()
    p.text = "• 100% EUDR Traceability: Full geolocation & deforestation-free proof."
    p = body.add_paragraph()
    p.text = "• +35% Farmer Income Increase: Via quality premiums & crop diversification."
    p = body.add_paragraph()
    p.text = "• 20%+ Women Leadership: Priority inclusion for women & youth (<35)."
    
    add_photo_placeholder(slide, Inches(8.5), Inches(2.5), Inches(4), Inches(3), "[ FOTO PETANI / IMPACT ]")

    # SLIDE 9: Contact & Closing
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "Let's Build Sustainable Agribusiness Together"
    subtitle.text = "PT Klumbayan Gold Farm\nwww.agrowforests.id | contact@klumbayangoldfarm.com\nHQ: Bandar Lampung & Gudang Natar, Lampung, Indonesia"

    add_photo_placeholder(slide, Inches(1.5), Inches(1), Inches(3), Inches(3), "[ FOTO LOGO KGF ]")
    add_photo_placeholder(slide, Inches(5.5), Inches(4), Inches(4.5), Inches(3), "[ FOTO TIM KGF ]")
    
    output_path = os.path.join(os.path.dirname(__file__), "c3_hsbc_pitch_deck.pptx")
    prs.save(output_path)
    print(f"Presentation saved to {output_path}")

if __name__ == '__main__':
    import pptx
    create_deck()
