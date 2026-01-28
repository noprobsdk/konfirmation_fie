#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import mimetypes
import os

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


def attach_inline_image(outer: MIMEMultipart, path: str, cid: str):
    """
    Attach ONE inline image (CID) without filename/name headers.
    This reduces the chance Gmail Android shows an attachment strip.
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

    # CID used by HTML
    img.add_header("Content-ID", f"<{cid}>")

    # Inline, with NO filename parameter
    img.add_header("Content-Disposition", "inline")

    # Ensure Content-Type doesn't carry a name= parameter
    img.replace_header("Content-Type", f"image/{subtype}")

    outer.attach(img)


def build_raw_message(sender: str, to: str, subject: str, image_path: str) -> str:
    """
    Image-only invitation email using a single inline CID image.
    No external images. No second image => no "double" on Gmail Android.
    """

    outer = MIMEMultipart("related")
    outer["To"] = to
    outer["From"] = sender
    outer["Subject"] = subject

    alt = MIMEMultipart("alternative")

    # Minimal plain part (keeps MIME valid, avoids showing extra text)
    alt.attach(MIMEText(" ", "plain", "utf-8"))

    html = """<!doctype html>
<html lang="da">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="x-apple-disable-message-reformatting">
  <title></title>
</head>
<body style="margin:0;padding:0;background:#f3f3f3;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f3f3f3;">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
               style="width:600px;max-width:600px;background:#ffffff;border-radius:18px;overflow:hidden;">
          <tr>
            <td style="padding:0;">
              <img src="cid:invite" width="600" alt=""
                   style="display:block;width:100%;max-width:600px;height:auto;border:0;outline:none;text-decoration:none;">
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    alt.attach(MIMEText(html, "html", "utf-8"))
    outer.attach(alt)

    # Attach exactly ONE image
    attach_inline_image(outer, image_path, "invite")

    return base64.urlsafe_b64encode(outer.as_bytes()).decode("utf-8")


def send_raw(raw: str):
    service = gmail_service()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


if __name__ == "__main__":
    load_dotenv()

    to_list = os.getenv("TO", "").strip()
    subject = os.getenv("SUBJECT", "Invitation til konfirmation – Fie Jochumsen")
    image_path = os.getenv("IMAGE_PATH", "invitation_outlook_baked.png")

    if not to_list:
        raise ValueError("TO missing in .env (example: TO=a@b.com,c@d.com)")

    recipients = [x.strip() for x in to_list.split(",") if x.strip()]

    for to in recipients:
        raw = build_raw_message(
            sender="me",
            to=to,
            subject=subject,
            image_path=image_path,
        )
        res = send_raw(raw)
        print(f"Sent to {to} ✅ Message ID: {res.get('id')}")
