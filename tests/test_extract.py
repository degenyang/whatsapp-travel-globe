"""Run scripts/extract.py on the fixture chats and check what lands in each year file.

    python -m pytest tests
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "chats"


def run_extract(tmp_path, *extra):
    out = tmp_path / "travel"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "extract.py"), str(FIX), str(out), *extra],
                   check=True, capture_output=True)
    return {p.stem: p.read_text(encoding="utf-8").splitlines() for p in sorted(out.glob("y*.txt"))}


def test_every_export_format(tmp_path):
    years = run_extract(tmp_path, "--me", "You", "--me", "Me Myself")
    assert years == {
        "y2019": [
            "2019-04-05 07:10 [android_24h] Me: boarding now, see you in Paris",
            "2019-04-08 21:40 [android_24h] Me: landed, back home",
        ],
        # continuation lines belong to the message above them
        "y2021": ["2021-06-14 09:00 [android_multiline] Me: quick update we just checked in at the hotel the view is great"],
        # iOS: [DD/MM/YYYY, HH:MM:SS], sender is your own name
        "y2023": ["2023-02-13 18:23 [ios_named] Me: I'm in Lisbon until Sunday"],
        # US: M/D/YY with AM/PM, also with the narrow no-break space newer phones write
        "y2024": [
            "2024-03-25 18:15 [us_ampm] Me: my flight is delayed again",
            "2024-03-28 11:02 [us_ampm] Me: just arrived in Tokyo",
        ],
        "y2025": [
            "2025-04-02 09:15 [us_nnbsp] Me: at the airport already",
            "2025-04-13 20:00 [us_nnbsp] Me: holiday is over",
        ],
    }


def test_date_order_override(tmp_path):
    # 4/2/25 read day-first is 4 Feb, not 2 Apr
    years = run_extract(tmp_path, "--date-order", "dmy")
    assert "2025-02-04 09:15 [us_nnbsp] Me: at the airport already" in years["y2025"]


def test_other_peoples_messages_are_dropped(tmp_path):
    years = run_extract(tmp_path)
    assert not any("Me Myself" in l or "Lisbon" in l for rows in years.values() for l in rows)
