"""Generate a demo dental-clinic knowledge base PDF for testing the agent's RAG.

Run:  .venv/bin/python scripts/make_demo_kb.py
Output: /tmp/brightsmile-dental-faq.pdf
"""
from fpdf import FPDF

SECTIONS = [
    (
        "About BrightSmile Dental",
        [
            "BrightSmile Dental is a family and cosmetic dental clinic located at "
            "240 Maple Avenue, Suite 5, Springfield. We have served the community "
            "for over 15 years and welcome both new and returning patients.",
            "Our team includes three dentists, two hygienists, and a friendly front-desk "
            "staff. We focus on gentle, anxiety-free care for patients of all ages.",
        ],
    ),
    (
        "Hours of Operation",
        [
            "Monday to Thursday: 8:00 AM to 6:00 PM.",
            "Friday: 8:00 AM to 2:00 PM.",
            "Saturday: 9:00 AM to 1:00 PM (cleanings and emergencies only).",
            "Sunday: Closed.",
            "We are closed on major public holidays.",
        ],
    ),
    (
        "Services We Offer",
        [
            "Routine cleanings and check-ups.",
            "Fillings, crowns, and bridges.",
            "Teeth whitening and cosmetic veneers.",
            "Root canal treatment.",
            "Tooth extractions, including wisdom teeth.",
            "Dental implants.",
            "Invisalign and orthodontic consultations.",
            "Pediatric dentistry for children aged 2 and up.",
        ],
    ),
    (
        "Pricing (Estimates)",
        [
            "New patient exam and X-rays: $95.",
            "Routine cleaning: $120.",
            "Teeth whitening (in-office): $350.",
            "Standard filling: $150 to $250 depending on size.",
            "Crown: $900 to $1,300.",
            "Root canal: $700 to $1,100 depending on the tooth.",
            "Prices are estimates; a precise quote is given after an exam.",
        ],
    ),
    (
        "Insurance and Payment",
        [
            "We accept most major PPO insurance plans, including Delta Dental, Cigna, "
            "Aetna, MetLife, and Guardian.",
            "We are not in-network with HMO plans but can provide a receipt for "
            "out-of-network reimbursement.",
            "Payment is due at the time of service. We accept cash, all major credit "
            "cards, and offer interest-free payment plans through CareCredit.",
            "For uninsured patients, we offer an in-house membership plan at $29 per "
            "month that includes two cleanings a year and 15% off other treatments.",
        ],
    ),
    (
        "Appointments and Cancellations",
        [
            "New patients should arrive 15 minutes early to complete paperwork, or fill "
            "out forms online beforehand.",
            "Please bring a photo ID and your insurance card to your first visit.",
            "We require at least 24 hours notice to cancel or reschedule. A $50 fee may "
            "apply for missed appointments or late cancellations.",
            "We send appointment reminders by text and email.",
        ],
    ),
    (
        "Dental Emergencies",
        [
            "For severe pain, swelling, a knocked-out tooth, or uncontrolled bleeding, "
            "call us immediately at (555) 200-1234 and we will try to see you the same day.",
            "If a tooth is knocked out, keep it moist in milk or saliva and come in within "
            "30 minutes for the best chance of saving it.",
            "Outside of business hours, our phone line provides an on-call emergency number.",
            "If you have difficulty breathing or swallowing, or severe facial swelling, go "
            "to the nearest emergency room.",
        ],
    ),
    (
        "New Patients and Parking",
        [
            "We are accepting new patients and would love to welcome you.",
            "Free parking is available in the lot behind the building and on Maple Avenue.",
            "The clinic is wheelchair accessible with an elevator to Suite 5.",
            "We offer free Wi-Fi and a children's play area in the waiting room.",
        ],
    ),
]


def main() -> None:
    pdf = FPDF()
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    content_w = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "BrightSmile Dental Clinic", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, "Patient Information & Frequently Asked Questions", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    for title, lines in SECTIONS:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for line in lines:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(content_w, 6, f"- {line}")
        pdf.ln(3)

    out = "/tmp/brightsmile-dental-faq.pdf"
    pdf.output(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
