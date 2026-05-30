"""Generate a demo hotel knowledge base PDF for the voice agent's RAG.

Run:  .venv/bin/python scripts/make_hotel_kb.py
Output: /tmp/grandplaza-hotel-info.pdf
"""
from fpdf import FPDF

SECTIONS = [
    (
        "About The Grand Plaza Hotel",
        [
            "The Grand Plaza is a 4-star boutique hotel at 88 Harbor Boulevard, "
            "downtown, a 10-minute drive from the international airport.",
            "We have 120 rooms across four categories, two restaurants, a rooftop "
            "pool, a spa, and a 24-hour front desk.",
        ],
    ),
    (
        "Room Types and Nightly Rates",
        [
            "Standard Queen: one queen bed, city view, sleeps 2. From $149 per night.",
            "Deluxe King: one king bed, high floor, sleeps 2. From $209 per night.",
            "Twin Double: two double beds, sleeps 4, great for families. From $229 per night.",
            "Executive Suite: separate living room, harbor view, sleeps 3. From $379 per night.",
            "Rates vary by date and availability; taxes are 12% additional.",
        ],
    ),
    (
        "Check-in, Check-out and Policies",
        [
            "Check-in is from 3:00 PM. Check-out is by 11:00 AM.",
            "Early check-in and late check-out are subject to availability and may "
            "incur a fee.",
            "Guests must be at least 18 and present a photo ID and the card used to book.",
            "Cancellations are free up to 48 hours before arrival; later cancellations "
            "are charged one night.",
            "The hotel is non-smoking. A cleaning fee applies to smoking in rooms.",
        ],
    ),
    (
        "Amenities",
        [
            "Free high-speed Wi-Fi throughout the hotel.",
            "Rooftop pool open 6 AM to 10 PM, and a fitness center open 24 hours.",
            "The Vista Spa offers massages and treatments, open 9 AM to 8 PM.",
            "Valet parking is $35 per night; self-parking is $22 per night.",
            "Pets under 25 lbs are welcome for a $50 per stay fee.",
        ],
    ),
    (
        "Dining",
        [
            "Harbor Grill serves breakfast 6:30-10:30 AM and dinner 5:30-10:30 PM.",
            "The Lobby Cafe serves coffee and light fare all day.",
            "Room service is available 24 hours.",
            "Complimentary breakfast is included with Executive Suite bookings.",
        ],
    ),
    (
        "Getting Here and Transport",
        [
            "From the airport, take Harbor Boulevard exit 4; we are on the right "
            "after the marina.",
            "Airport shuttle runs every 30 minutes from 5 AM to midnight for $15 per "
            "person; reserve at the front desk.",
            "The downtown train station is a 5-minute walk away.",
        ],
    ),
    (
        "Reservations and Groups",
        [
            "We accept reservations by phone and welcome walk-ins subject to availability.",
            "A valid card holds the reservation; you are charged at check-out.",
            "For groups of 8 rooms or more, ask about group rates and our event spaces.",
            "Confirmation is sent by text and email once the front desk finalizes a booking.",
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
    pdf.cell(0, 12, "The Grand Plaza Hotel", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, "Guest Information & Frequently Asked Questions", new_x="LMARGIN", new_y="NEXT")
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

    out = "/tmp/grandplaza-hotel-info.pdf"
    pdf.output(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
