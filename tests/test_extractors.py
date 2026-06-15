from extractors.email_extractor import extract_emails, guess_role_from_email
from extractors.phone_extractor import extract_whatsapp
from extractors.social_extractor import extract_social
from extractors.person_extractor import extract_people


def test_email_basic():
    html = '<a href="mailto:Founder@Acme.com">mail</a> hello [at] acme [dot] com'
    out = extract_emails(html)
    assert "founder@acme.com" in out
    assert "hello@acme.com" in out


def test_guess_role_from_email():
    assert guess_role_from_email("founder@acme.com") == "Founder"
    assert guess_role_from_email("random@acme.com") is None


def test_whatsapp():
    html = '<a href="https://wa.me/628123456789">WA</a>'
    out = extract_whatsapp(html)
    assert "+628123456789" in out


def test_social():
    html = '<a href="https://www.linkedin.com/company/acme">li</a>' \
           '<a href="https://t.me/acme_official">tg</a>'
    out = extract_social(html)
    assert "linkedin" in out and "telegram" in out


def test_people():
    html = """
    <div class="team">
      <h3>Jane Doe</h3>
      <p>CEO & Co-Founder of Acme</p>
    </div>
    """
    people = extract_people(html)
    roles = {p.role for p in people}
    assert {"CEO", "Founder"} & roles
