"""Round 32 B1 reverse-split round-up watch: which sentences qualify. No network."""
from swingtrader.daily import roundup_watch as w


def test_forward_round_up_sentence_qualifies():
    t = ("<p>No fractional shares will be issued in connection with the Reverse Stock Split, and any fractional shares "
         "resulting from the Reverse Stock Split will be rounded up to the nearest whole share.</p>")
    assert "rounded up" in w.round_up_sentence(t)


def test_cash_in_lieu_option_and_past_tense_do_not():
    cash = ("Stockholders who would otherwise be entitled to a fractional share as a result of the reverse split will "
            "receive a cash payment in lieu of such fractional share, or such fraction will be rounded up.")
    option = ("The Board may elect to issue fractions, or to entitle shareholders to receive, in lieu of any fractional "
              "share, the number of shares rounded up to the next whole number following the reverse split.")
    past = "Any fractional shares resulting from the Reverse Stock Split were rounded up to the nearest whole share."
    assert w.round_up_sentence(cash) is None
    assert w.round_up_sentence(option) is None
    assert w.round_up_sentence(past) is None


def test_unrelated_round_up_text_does_not_qualify():
    reit = ("that number of shares (rounded up to the nearest whole share) in excess of the ownership limit will be "
            "transferred to a charitable trust.")
    assert w.round_up_sentence(reit) is None


def test_participant_level_language_is_caught():
    t = "fractional shares will be rounded up to the nearest whole share at the participant level"
    assert w.PL.search(t)


def test_whole_share_in_lieu_wording_qualifies():
    t = ("If as a result of the reverse stock split a stockholder would otherwise hold a fractional share, the stockholder "
         "will receive one whole share in lieu of the issuance of any such fractional share.")
    assert w.round_up_sentence(t) is not None
    cash = ("Stockholders who would otherwise hold a fractional share as a result of the reverse stock split will receive "
            "cash in lieu of the fractional share.")
    assert w.round_up_sentence(cash) is None
