#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import mimetypes
import os
import html

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def gmail_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "Missing credentials.json. Create an OAuth Desktop client in Google Cloud Console and download it."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def parse_recipients(value: str) -> list[str]:
    """
    Accepts comma OR newline separated recipients.
    """
    if not value:
        return []
    # allow both commas + newlines
    raw = value.replace("\n", ",")
    return [x.strip() for x in raw.split(",") if x.strip()]


def attach_inline_image(outer: MIMEMultipart, path: str, cid: str):
    """
    Attach ONE inline image (CID) without filename/name params.
    This reduces attachment-strip issues in Gmail Android.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing image file: {path}")

    with open(path, "rb") as f:
        data = f.read()

    ctype, _ = mimetypes.guess_type(path)
    if not ctype:
        ctype = "image/png"

    maintype, subtype = ctype.split("/", 1)
    if maintype != "image":
        raise ValueError(f"Not an image: {path} (type={ctype})")

    img = MIMEImage(data, _subtype=subtype)
    img.add_header("Content-ID", f"<{cid}>")
    img.add_header("Content-Disposition", "inline")
    img.replace_header("Content-Type", f"image/{subtype}")

    outer.attach(img)


def build_plain_text(preheader: str, name: str, date: str, time_: str,
                     address: str, deadline: str, signoff: str) -> str:
    parts = []
    if preheader.strip():
        parts.append(preheader.strip())
        parts.append("")

    parts.append("Invitation til konfirmation")
    parts.append("")
    parts.append(f"{name}s konfirmation")
    parts.append(date)
    parts.append(time_)
    parts.append("")
    parts.append("Vi håber, at I vil være med til at fejre dagen sammen med os med god mad, hyggeligt samvær og festlig stemning.")
    parts.append("")
    parts.append(f"Adresse: {address}")
    parts.append(f"Tilmelding senest: {deadline}")
    parts.append("")
    parts.append("Kærlig hilsen")
    parts.append(signoff)

    return "\n".join(parts).strip() + "\n"


def build_raw_message(sender: str, to: str, subject: str, html_title: str,
                      image_path: str, preheader: str,
                      name: str, date: str, time_: str,
                      address: str, deadline: str, signoff: str) -> str:
    """
    Invitation email with:
    - Plain-text version
    - HTML version with hidden preheader + <title>
    - ONE inline image (CID)
    """
    outer = MIMEMultipart("related")
    outer["To"] = to
    outer["From"] = sender
    outer["Subject"] = subject

    alt = MIMEMultipart("alternative")

    # Plain text
    plain = build_plain_text(preheader, name, date, time_, address, deadline, signoff)
    alt.attach(MIMEText(plain, "plain", "utf-8"))

    # Escape for safe HTML insertion
    safe_title = html.escape(html_title or "")
    safe_preheader = html.escape((preheader or "").strip() or " ")

    html_body = f"""<!doctype html>
<html lang="da">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title>{safe_title}</title>
</head>

<body style="margin:0;padding:0;background:#f3f3f3;">

  <!-- Preheader (hidden) -->
  <div style="display:none;font-size:1px;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;mso-hide:all;">
    {safe_preheader}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f3f3f3;">
    <tr>
      <td align="center" style="padding:28px 12px; text-align:center;">

        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               width="600"
               style="width:600px; max-width:600px; margin:0 auto;">
          <tr>
            <td align="center" style="padding:0; text-align:center;">

              <img
                src="cid:invite"
                width="600"
                alt="Invitation til konfirmation"
                style="display:block; width:600px; max-width:100%; height:auto; margin:0 auto; border:0; outline:none; text-decoration:none;"
              >

            </td>
          </tr>
        </table>

      </td>
    </tr>
  </table>
</body>
</html>
"""
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    outer.attach(alt)

    # Inline image
    attach_inline_image(outer, image_path, "invite")

    return base64.urlsafe_b64encode(outer.as_bytes()).decode("utf-8")


def send_raw(raw: str):
    service = gmail_service()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_variant(*, sender: str, subject: str, html_title: str,
                 recipients: list[str],
                 image_path: str, preheader: str,
                 name: str, date: str, time_: str, address: str,
                 deadline: str, signoff: str,
                 label: str):
    if not recipients:
        return

    for to in recipients:
        raw = build_raw_message(
            sender=sender,
            to=to,
            subject=subject,
            html_title=html_title,
            image_path=image_path,
            preheader=preheader,
            name=name,
            date=date,
            time_=time_,
            address=address,
            deadline=deadline,
            signoff=signoff,
        )
        res = send_raw(raw)
        print(f"[{label}] Sent to {to} ✅ Message ID: {res.get('id')}")


if __name__ == "__main__":
    load_dotenv()

    # Global/common
    sender = os.getenv("SENDER", "Fie Jochumsen <henrik.jochumsen@gmail.com>").strip()
    subject = os.getenv("SUBJECT", "Invitation til konfirmation – Fie Jochumsen").strip()
    html_title = os.getenv("HTML_TITLE", subject).strip()

    name = os.getenv("INV_NAME", "Fie Jochumsen").strip()
    date = os.getenv("INV_DATE", "Lørdag d. 25. april 2026").strip()
    deadline = os.getenv("INV_DEADLINE", "24/3").strip()
    signoff = os.getenv("INV_SIGNOFF", "Fie & familien").strip()

    # Recipient groups
    to_church = parse_recipients(os.getenv("TO_CHURCH", ""))
    to_home = parse_recipients(os.getenv("TO_HOME", ""))

    
    # Variant 1 (Church)
    preheader_1 = os.getenv("PREHEADER_1", "").strip()
    time_1 = os.getenv("INV_TIME_1", "Kl. 14.00").strip()
    address_1 = os.getenv("INV_ADDRESS_1", "").strip()
    image_1 = os.getenv("IMAGE_PATH_1", "").strip()

    # Variant 2 (Home / after church)
    preheader_2 = os.getenv("PREHEADER_2", "").strip()
    time_2 = os.getenv("INV_TIME_2", "Kl. 16.00").strip()
    address_2 = os.getenv("INV_ADDRESS_2", "").strip()
    image_2 = os.getenv("IMAGE_PATH_2", "").strip()

    if not (to_church or to_home ):
        raise ValueError("No recipients. Set TO_CHURCH and/or TO_HOME.")

    # Basic safety checks for required images if that variant will be sent
    if not image_1:
        raise ValueError("IMAGE_PATH_1 is required when sending church variant.")
    if not image_2:
        raise ValueError("IMAGE_PATH_2 is required when sending home variant.")

    # Send to real groups
    send_variant(
        sender=sender, subject=subject, html_title=html_title,
        recipients=to_church,
        image_path=image_1, preheader=preheader_1,
        name=name, date=date, time_=time_1, address=address_1,
        deadline=deadline, signoff=signoff,
        label="CHURCH"
    )

    send_variant(
        sender=sender, subject=subject, html_title=html_title,
        recipients=to_home,
        image_path=image_2, preheader=preheader_2,
        name=name, date=date, time_=time_2, address=address_2,
        deadline=deadline, signoff=signoff,
        label="HOME"
    )

    