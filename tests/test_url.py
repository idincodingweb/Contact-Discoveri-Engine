from utils.url import base_domain, normalize, is_target_page, same_site


def test_normalize():
    assert normalize("nike.com") == "https://nike.com/"
    assert normalize("https://Nike.com/about/") == "https://nike.com/about"


def test_base_domain():
    assert base_domain("https://www.nike.com/about") == "nike.com"
    assert base_domain("https://shop.nike.co.uk/x") == "nike.co.uk"


def test_target():
    assert is_target_page("https://x.com/about")
    assert not is_target_page("https://x.com/blog/post-1")


def test_same_site():
    assert same_site("https://nike.com/a", "https://www.nike.com/b")
    assert not same_site("https://nike.com", "https://adidas.com")
