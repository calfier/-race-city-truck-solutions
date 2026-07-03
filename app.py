from flask import Flask, request, jsonify
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import smtplib
import ssl
import traceback
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import io
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000",
     "http://localhost:3001", "https://racecitytrucksolutions.com",
                   "https://www.racecitytrucksolutions.com"])

# ── Email Configuration ──────────────────────────────────────────
# Pulled from environment variables — set these in Render's dashboard
# under Environment. Never hardcode credentials in source code.
EMAIL_HOST = os.environ.get("EMAIL_HOST",     "smtp.hostinger.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 465))
EMAIL_USER = os.environ.get("EMAIL_USER",     "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_TO",       "info@racecitytrucksolutions.com")

print("DEBUG: env keys containing EMAIL:", [repr(k) for k in os.environ if "EMAIL" in k.upper()])

if not EMAIL_USER or not EMAIL_PASSWORD:
    print("WARNING: EMAIL_USER or EMAIL_PASSWORD environment variables are not set.")
else:
    print("Email configured for:", EMAIL_USER)
# ────────────────────────────────────────────────────────────────

ACCENT_COLOR = HexColor("#29c4f2")
DARK_COLOR = HexColor("#1a1a1a")
GRAY_COLOR = HexColor("#666666")
LIGHT_GRAY = HexColor("#f5f5f5")


def generate_pdf(data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch
    )

    elements = []

    # ── Header
    header_data = [[
        Paragraph(
            '<font name="Helvetica-Bold" size="16" color="white">RACE CITY TRUCK SOLUTIONS</font>',
            ParagraphStyle("header", fontName="Helvetica", alignment=TA_LEFT)
        ),
        Paragraph(
            '<font name="Helvetica-Bold" size="11" color="white">SERVICE REQUEST</font><br/>'
            '<font name="Helvetica" size="9" color="white">'
            + datetime.now().strftime("%B %d, %Y") +
            '</font>',
            ParagraphStyle("headerRight", fontName="Helvetica",
                           alignment=TA_LEFT)
        )
    ]]

    header_table = Table(header_data, colWidths=[4.5 * inch, 2.5 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_COLOR),
        ("TEXTCOLOR",  (0, 0), (-1, -1), white),
        ("PADDING",    (0, 0), (-1, -1), 16),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * inch))

    # ── Styles
    section_style = ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=ACCENT_COLOR,
        spaceAfter=8,
    )
    label_style = ParagraphStyle(
        "label",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=DARK_COLOR,
    )
    value_style = ParagraphStyle(
        "value",
        fontName="Helvetica",
        fontSize=10,
        textColor=GRAY_COLOR,
    )

    # ── Contact Information
    elements.append(Paragraph("CONTACT INFORMATION", section_style))
    elements.append(HRFlowable(width="100%", thickness=1,
                    color=ACCENT_COLOR, spaceAfter=8))

    contact_data = [
        ["Full Name",  data.get("name",    "N/A")],
        ["Company",    data.get("company", "N/A") or "N/A"],
        ["Phone",      data.get("phone",   "N/A")],
        ["Email",      data.get("email",   "N/A")],
    ]
    contact_table = Table(
        [[Paragraph(l, label_style), Paragraph(v, value_style)]
         for l, v in contact_data],
        colWidths=[2 * inch, 5 * inch]
    )
    contact_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, LIGHT_GRAY]),
        ("PADDING",        (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(contact_table)
    elements.append(Spacer(1, 0.25 * inch))

    # ── Service Details
    elements.append(Paragraph("SERVICE DETAILS", section_style))
    elements.append(HRFlowable(width="100%", thickness=1,
                    color=ACCENT_COLOR, spaceAfter=8))

    services = data.get("services", [])
    service_str = ", ".join(services) if services else "N/A"

    service_data = [
        ["Number of Trucks",   data.get("truckCount", "N/A") or "N/A"],
        ["Services Requested", service_str],
    ]
    service_table = Table(
        [[Paragraph(l, label_style), Paragraph(v, value_style)]
         for l, v in service_data],
        colWidths=[2 * inch, 5 * inch]
    )
    service_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, LIGHT_GRAY]),
        ("PADDING",        (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(service_table)
    elements.append(Spacer(1, 0.25 * inch))

    # ── Notes
    elements.append(Paragraph("ADDITIONAL NOTES", section_style))
    elements.append(HRFlowable(width="100%", thickness=1,
                    color=ACCENT_COLOR, spaceAfter=8))
    notes = data.get("notes", "").strip() or "No additional notes provided."
    elements.append(Paragraph(notes, value_style))
    elements.append(Spacer(1, 0.5 * inch))

    # ── Footer
    footer_table = Table([[
        Paragraph(
            '<font name="Helvetica" size="8" color="white">'
            + str(datetime.now().year) +
            ' Race City Truck Solutions  |  Auto-generated from service request form.'
            '</font>',
            ParagraphStyle("footer", fontName="Helvetica", alignment=TA_CENTER)
        )
    ]], colWidths=[7 * inch])
    footer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_COLOR),
        ("PADDING",    (0, 0), (-1, -1), 10),
    ]))
    elements.append(footer_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def send_email(data, pdf_buffer):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = "New Service Request - " + data.get("name", "Unknown")

    body = """
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0;">
        <div style="background: #29c4f2; padding: 24px 20px;">
            <h2 style="color: #1a1a1a; margin: 0;">RACE CITY TRUCK SOLUTIONS</h2>
            <p style="color: #1a1a1a; margin: 6px 0 0; font-size: 13px;">New Service Request Received</p>
        </div>
        <div style="padding: 24px 20px;">
            <p>A new service request has been submitted. See the attached PDF for full details.</p>
            <table style="width:100%; border-collapse:collapse; font-size:14px;">
                <tr style="background:#f5f5f5;">
                    <td style="padding:10px 14px; font-weight:bold; width:160px;">Customer</td>
                    <td style="padding:10px 14px;">{name}</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; font-weight:bold;">Company</td>
                    <td style="padding:10px 14px;">{company}</td>
                </tr>
                <tr style="background:#f5f5f5;">
                    <td style="padding:10px 14px; font-weight:bold;">Phone</td>
                    <td style="padding:10px 14px;">{phone}</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; font-weight:bold;">Email</td>
                    <td style="padding:10px 14px;">{email}</td>
                </tr>
                <tr style="background:#f5f5f5;">
                    <td style="padding:10px 14px; font-weight:bold;">Services</td>
                    <td style="padding:10px 14px;">{services}</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; font-weight:bold;">Trucks</td>
                    <td style="padding:10px 14px;">{truck_count}</td>
                </tr>
                <tr style="background:#f5f5f5;">
                    <td style="padding:10px 14px; font-weight:bold;">Notes</td>
                    <td style="padding:10px 14px;">{notes}</td>
                </tr>
            </table>
        </div>
        <div style="background:#1a1a1a; padding:16px 20px; text-align:center;">
            <p style="color:#666; font-size:12px; margin:0;">
                Race City Truck Solutions &nbsp;|&nbsp; Statesville, NC &nbsp;|&nbsp; (704) 555-0199
            </p>
        </div>
    </body>
    </html>
    """.format(
        name=data.get("name",      "N/A"),
        company=data.get("company",   "N/A") or "N/A",
        phone=data.get("phone",     "N/A"),
        email=data.get("email",     "N/A"),
        services=", ".join(data.get("services", [])) or "N/A",
        truck_count=data.get("truckCount", "N/A") or "N/A",
        notes=data.get("notes",     "None provided") or "None provided",
    )

    msg.attach(MIMEText(body, "html"))

    pdf_bytes = pdf_buffer.read()
    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    filename = "Race-City-Service-Request-" + \
        data.get("name", "Request").replace(" ", "-") + ".pdf"
    attachment.add_header("Content-Disposition",
                          "attachment", filename=filename)
    msg.attach(attachment)

    if EMAIL_PORT == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
    else:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())


# ── Routes ───────────────────────────────────────────────────────

@app.route("/api/service-request", methods=["POST"])
def service_request():
    try:
        print("=== Request received ===")
        data = request.get_json()
        print("Data:", data)

        if not data:
            print("ERROR: No data received")
            return jsonify({"error": "No data received"}), 400

        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("ERROR: Email credentials not configured")
            return jsonify({"error": "Email not configured on server"}), 500

        required = ["name", "email", "phone", "services"]
        for field in required:
            if not data.get(field):
                print("ERROR: Missing field:", field)
                return jsonify({"error": "Missing required field: " + field}), 400

        print("Generating PDF...")
        pdf_buffer = generate_pdf(data)
        print("PDF generated successfully")

        print("Sending email to:", EMAIL_TO)
        print("Using SMTP host:", EMAIL_HOST, "port:", EMAIL_PORT)
        print("Logging in as:", EMAIL_USER)
        send_email(data, pdf_buffer)
        print("Email sent successfully!")

        return jsonify({"success": True, "message": "Service request sent successfully"}), 200

    except smtplib.SMTPAuthenticationError as e:
        print("SMTP AUTH ERROR:", str(e))
        return jsonify({"error": "Email authentication failed."}), 500

    except smtplib.SMTPConnectError as e:
        print("SMTP CONNECT ERROR:", str(e))
        return jsonify({"error": "Could not connect to email server."}), 500

    except smtplib.SMTPException as e:
        print("SMTP ERROR:", str(e))
        return jsonify({"error": "Email sending failed: " + str(e)}), 500

    except Exception as e:
        print("UNEXPECTED ERROR:", str(e))
        traceback.print_exc()
        return jsonify({"error": "Server error: " + str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "email_configured": bool(EMAIL_USER and EMAIL_PASSWORD)
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
