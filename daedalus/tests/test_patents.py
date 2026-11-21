"""Patent-office connector tests."""

from uuid import UUID

import httpx
from delphi_contracts.enums import WorkKind

from daedalus.cli import _bearer, _epo_bearer_headers, _header, main
from daedalus.connectors import from_epo, from_lens, from_patsnap, from_wipo
from daedalus.fetch import FetchError
from daedalus.patents import (
    epo_access_token,
    fetch_epo,
    fetch_lens,
    fetch_patent_slice,
    fetch_patsnap,
    fetch_wipo,
    search_epo,
    search_lens,
    search_patsnap,
    search_wipo,
)


def _epo_payload() -> dict[str, object]:
    return {
        "ops:world-patent-data": {
            "ops:biblio-search": {
                "ops:search-result": {
                    "exchange-documents": {
                        "exchange-document": {
                            "bibliographic-data": {
                                "publication-reference": {
                                    "document-id": {
                                        "country": {"$": "EP"},
                                        "doc-number": {"$": "1234567"},
                                        "kind": {"$": "A1"},
                                        "date": {"$": "20140115"},
                                    }
                                },
                                "invention-title": [
                                    {"$": "QR overlay", "@lang": "en"},
                                    {"$": "Deutsch", "@lang": "de"},
                                ],
                                "parties": {
                                    "inventors": {
                                        "inventor": {"inventor-name": {"$": "Ada"}}
                                    }
                                },
                                "classifications-cpc": {
                                    "classification-cpc": {"symbol": {"$": "G06K19/06"}}
                                },
                            },
                            "abstract": {"p": {"$": "A QR code overlay."}},
                        }
                    }
                }
            }
        }
    }


def test_epo_token_and_biblio_mapping() -> None:
    """Verify this behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        if request.method == "POST":
            assert b"grant_type=client_credentials" in request.content
            return httpx.Response(200, json={"access_token": "tok"})
        return httpx.Response(200, json=_epo_payload())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert epo_access_token(client, "key", "secret") == "tok"
    rows = fetch_epo("https://ops.epo.org/search", "two_d_codes", client)
    assert len(rows) == 1
    assert rows[0]["patent"].startswith("EP1234567")
    assert rows[0]["title"] == "QR overlay"
    assert rows[0]["published_on"] == "2014-01-15"
    assert "Ada" in rows[0]["authors"]
    work = from_epo(
        {
            "id": rows[0]["id"],
            "title": rows[0]["title"],
            "published_on": rows[0]["published_on"],
            "patent": rows[0]["patent"],
        },
        "two_d_codes",
    )
    assert work.kind is WorkKind.PATENT
    assert UUID(rows[0]["id"])
    searched = search_epo("QR", "two_d_codes", client, limit=10)
    assert searched


def test_wipo_patsnap_lens_and_poison_skip() -> None:
    """Verify this behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        url = str(request.url)
        if "wipo" in url or "patentscope" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        "skip",
                        {
                            "publicationNumber": "WO2010123456",
                            "title": "PCT QR carrier",
                            "publicationDate": "2010-06-01",
                            "abstract": "PCT filing",
                            "inventors": [{"name": "Kim"}],
                            "ipc": ["G06K"],
                        },
                    ]
                },
            )
        if "patsnap" in url or "query-search-patent" in url:
            return httpx.Response(
                200,
                json={
                    "status": True,
                    "error_code": 0,
                    "data": {
                        "results": [
                            {
                                "pn": "US11205304B2",
                                "title": "QR overlay patent",
                                "pbdt": 20140115,
                                "inventor": "ELSHAFIE, AHMED | YANG, WEI",
                                "authority": "US",
                                "patent_id": "718ead9c-4f3c-4674-8f5a-24e126827269",
                            }
                        ]
                    },
                },
            )
        if "lens.org" in url:
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "data": [
                        {
                            "lens_id": "031-156-664-516-153",
                            "jurisdiction": "EP",
                            "doc_number": "2471949",
                            "date_published": "2012-07-04",
                            "doc_key": "EP_2471949_A1_20120704",
                            "biblio": {
                                "invention_title": [
                                    {"text": "DE title", "lang": "de"},
                                    {"text": "Method for QR overlay", "lang": "en"},
                                ],
                                "parties": {
                                    "inventors": [
                                        {"extracted_name": {"value": "OCHOA JORGE"}},
                                    ]
                                },
                                "classifications_cpc": {
                                    "classifications": [{"symbol": "G06K19/06"}]
                                },
                                "claims": [
                                    {"claim_text": "A method for overlaying a QR code."}
                                ],
                                "abstracts": [{"lang": "en", "text": "A method."}],
                            },
                        }
                    ],
                },
            )
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    wipo = fetch_wipo(
        "https://patentscope.wipo.int/search/rest/patents?q=QR",
        "two_d_codes",
        client,
    )
    assert wipo[0]["patent"] == "WO2010123456"
    assert (
        from_wipo(
            {
                "id": wipo[0]["id"],
                "title": wipo[0]["title"],
                "published_on": wipo[0]["published_on"],
                "patent": wipo[0]["patent"],
            },
            "two_d_codes",
        ).kind
        is WorkKind.PATENT
    )
    snap = search_patsnap("QR", "two_d_codes", client)
    assert snap[0]["published_on"] == "2014-01-15"
    assert "AHMED" in snap[0]["authors"][0]
    assert from_patsnap(
        {
            "id": snap[0]["id"],
            "title": snap[0]["title"],
            "published_on": snap[0]["published_on"],
            "patent": snap[0]["patent"],
        },
        "two_d_codes",
    )
    lens = search_lens("QR", "two_d_codes", client)
    assert "Method for QR overlay" in lens[0]["title"]
    assert "OCHOA JORGE" in lens[0]["authors"]
    assert lens[0]["claims"]
    assert from_lens(
        {
            "id": lens[0]["id"],
            "title": lens[0]["title"],
            "published_on": lens[0]["published_on"],
            "patent": lens[0]["patent"],
        },
        "two_d_codes",
    )
    searched = search_wipo("QR", "two_d_codes", client)
    assert searched


def test_fetch_patent_slice_skips_missing_credentials_and_retries() -> None:
    """Verify this behavior."""
    empty = httpx.Client(
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={}))
    )
    assert not fetch_patent_slice(empty, per_subcategory=1)

    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        calls["n"] += 1
        if request.method == "POST" and "accesstoken" in str(request.url):
            return httpx.Response(200, json={"access_token": "tok"})
        if calls["n"] < 3:
            return httpx.Response(500)
        return httpx.Response(200, json=_epo_payload())

    client = httpx.Client(transport=httpx.MockTransport(flaky))
    rows = fetch_patent_slice(
        client,
        per_subcategory=1,
        epo_key="k",
        epo_secret="s",
        lens_token="",
    )
    assert rows
    dead = httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(500)))
    try:
        epo_access_token(dead, "k", "s", attempts=2)
    except FetchError:
        pass
    else:
        raise AssertionError("expected FetchError")
    try:
        fetch_lens(
            "https://api.lens.org/patent/search",
            "two_d_codes",
            dead,
            body={"query": {}},
            attempts=1,
        )
    except FetchError:
        pass
    else:
        raise AssertionError("expected FetchError")
    try:
        fetch_epo("https://ops.example/fail", "two_d_codes", dead, attempts=1)
    except FetchError:
        return
    raise AssertionError("expected FetchError")


def test_simple_payloads_token_miss_and_cv_filter() -> None:
    """Verify this behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        url = str(request.url)
        if "accesstoken" in url:
            return httpx.Response(200, json={"token_type": "Bearer"})
        if "publications" in url:
            return httpx.Response(
                200,
                json={
                    "publications": [
                        {
                            "patent_id": "EP1",
                            "title": "Simple QR",
                            "publication_date": "2011-01-01",
                            "authors": ["Ada"],
                            "claims": "A QR overlay on a carrier.",
                        }
                    ]
                },
            )
        if request.method == "GET" and "patsnap" in url:
            return httpx.Response(200, json={"results": []})
        if request.method == "GET" and "lens" in url:
            return httpx.Response(200, json={"data": []})
        if "wipo-nested" in url:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "results": [
                            {"id": "WO1", "title": "Nested", "date": "2012-02-02"}
                        ]
                    }
                },
            )
        return httpx.Response(200, json=["nope"])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        epo_access_token(client, "k", "s", attempts=1)
    except FetchError:
        pass
    else:
        raise AssertionError("expected FetchError")
    simple = fetch_epo("https://ops.example/publications", "two_d_codes", client)
    assert simple[0]["title"] == "Simple QR"
    assert simple[0]["claims"] == ["A QR overlay on a carrier."]
    assert not fetch_patsnap("https://connect.patsnap.com/x", "two_d_codes", client)
    assert not fetch_lens("https://api.lens.org/patent/search", "two_d_codes", client)
    nested = fetch_wipo("https://wipo-nested.test/x", "two_d_codes", client)
    assert nested[0]["patent"] == "WO1"
    assert not fetch_epo("https://ops.example/listish", "two_d_codes", client)

    def cv(_request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        if _request.method == "POST" and "accesstoken" in str(_request.url):
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(
            200,
            json={
                "publications": [
                    {
                        "patent_id": "US-MED",
                        "title": "Radiology medical imaging",
                        "publication_date": "2015-01-01",
                        "abstract": "autonomous driving detector",
                    }
                ]
            },
        )

    cv_client = httpx.Client(transport=httpx.MockTransport(cv))
    kept = fetch_patent_slice(cv_client, per_subcategory=5, epo_key="k", epo_secret="s")
    assert all(
        row["subcategory"] != "computer_vision" or "medical" not in row["title"].lower()
        for row in kept
    )


def test_alternate_shapes_dedupe_and_header_restore() -> None:
    """Verify this behavior."""
    iso_doc = {
        "document-id": [
            {
                "country": "US",
                "doc-number": "99",
                "kind": 1,
                "date": {"$": "2014-01-15T00:00:00"},
            }
        ],
        "invention-title": "ISO QR date",
        "parties": {"inventors": ["skip", {"name": "Pat"}]},
        "patent-classifications": {
            "patent-classification": {"classification-symbol": "G06K"}
        },
        "abstract": "barcode",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        url = str(request.url)
        if "accesstoken" in url:
            return httpx.Response(200, json={"access_token": "tok"})
        if request.method == "GET" and "ops" in url:
            return httpx.Response(
                200, json={"results": [iso_doc, True, {"title": "missing id"}]}
            )
        if "patentscope" in url or "wipo" in url:
            return httpx.Response(
                200,
                json={
                    "patents": [
                        {
                            "publication_number": "us-99",
                            "inventionTitle": "Dup QR",
                            "publication_date": "2014-01-15",
                            "inventors": "Ada, Kim",
                            "cpc": [{"symbol": "G06K"}, "G06V"],
                        }
                    ]
                },
            )
        if "patsnap" in url or "query-search-patent" in url:
            return httpx.Response(
                200,
                json=[
                    {
                        "patent_number": "US99",
                        "title": "PatSnap QR",
                        "publication_date": "20140115",
                        "inventors": [{"display_name": "Lee"}],
                    }
                ],
            )
        if "lens.org" in url:
            return httpx.Response(
                200,
                json=[
                    {
                        "jurisdiction": "US",
                        "doc_number": "99",
                        "title": "Lens QR",
                        "date_published": "2014-01-15",
                        "biblio": {
                            "invention_title": "not-a-list",
                            "abstract": {"text": "from dict"},
                            "parties": {"inventors": {"name": "nope"}},
                            "classifications_cpc": [],
                        },
                    }
                ],
            )
        return httpx.Response(200, json=False)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    client.headers["Authorization"] = "keep-me"
    rows = fetch_patent_slice(
        client,
        per_subcategory=8,
        epo_key="k",
        epo_secret="s",
        wipo_key="w",
        wipo_url="https://patentscope.wipo.int/search/rest/patents",
        patsnap_key="p",
        lens_token="l",
    )
    assert client.headers["Authorization"] == "keep-me"
    patents = {row["patent"] for row in rows}
    assert "US991" in patents or "US99" in patents
    assert not fetch_epo("https://example.test/empty", "two_d_codes", client)
    docs = fetch_wipo("https://wipo.test/docs", "two_d_codes", client)
    assert docs
    snap = fetch_patsnap("https://connect.patsnap.com/list", "two_d_codes", client)
    assert snap[0]["authors"] == ["Lee"]
    lens = fetch_lens("https://api.lens.org/patent/search", "two_d_codes", client)
    assert lens[0]["abstract"] == "from dict"


def test_lens_abstract_variants_and_wipo_docs() -> None:
    """Verify this behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        url = str(request.url)
        if "abstract-str" in url:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "lens_id": "1",
                            "jurisdiction": "EP",
                            "doc_number": "1",
                            "date_published": "2011-01-01",
                            "title": "QR string abstract",
                            "biblio": {
                                "invention_title": [
                                    {"text": "QR string abstract", "lang": "en"}
                                ],
                                "abstracts": "plain abstract",
                                "parties": {
                                    "inventors": [
                                        "skip",
                                        {"name": "Ada"},
                                        {"extracted_name": {"value": "Kim"}},
                                    ]
                                },
                                "classifications_cpc": {
                                    "classifications": ["skip", {"symbol": "X"}]
                                },
                            },
                        }
                    ]
                },
            )
        if "abstract-list" in url:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "lens_id": "2",
                            "doc_number": "2",
                            "date_published": "2011-02-02",
                            "biblio": {
                                "invention_title": [{"text": "QR fallback title"}],
                                "abstracts": [{"text": "fallback abs"}],
                            },
                        }
                    ]
                },
            )
        if "wipo-docs" in url:
            return httpx.Response(
                200,
                json={
                    "docs": [{"id": "WO2", "title": "Docs QR", "date": "2013-03-03"}]
                },
            )
        if "wipo-empty" in url:
            return httpx.Response(200, json={"meta": {}})
        return httpx.Response(200, json={"foo": 1})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    str_abs = fetch_lens("https://api.lens.org/abstract-str", "two_d_codes", client)
    assert str_abs[0]["abstract"] == "plain abstract"
    assert "Ada" in str_abs[0]["authors"]
    listed = fetch_lens("https://api.lens.org/abstract-list", "two_d_codes", client)
    assert listed[0]["title"] == "QR fallback title"
    assert listed[0]["abstract"] == "fallback abs"
    assert (
        fetch_wipo("https://wipo-docs.test/x", "two_d_codes", client)[0]["patent"]
        == "WO2"
    )
    assert not fetch_wipo("https://wipo-empty.test/x", "two_d_codes", client)
    assert not fetch_epo("https://ops.example/none", "two_d_codes", client)
    assert not fetch_patsnap("https://connect.patsnap.com/none", "two_d_codes", client)
    assert not fetch_lens("https://api.lens.org/none", "two_d_codes", client)


def test_cli_patent_flags(monkeypatch, tmp_path) -> None:
    """Verify this behavior."""

    class _CM:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("daedalus.cli.httpx.Client", lambda **_k: _CM())
    monkeypatch.setattr("daedalus.cli._epo_bearer_headers", lambda: {})
    monkeypatch.setattr("daedalus.cli.fetch_epo", lambda *_a, **_k: [{"title": "e"}])
    monkeypatch.setattr("daedalus.cli.fetch_wipo", lambda *_a, **_k: [{"title": "w"}])
    monkeypatch.setattr(
        "daedalus.cli.fetch_patsnap", lambda *_a, **_k: [{"title": "p"}]
    )
    monkeypatch.setattr("daedalus.cli.fetch_lens", lambda *_a, **_k: [{"title": "l"}])
    monkeypatch.setattr(
        "daedalus.cli.fetch_patent_slice", lambda *_a, **_k: [{"title": "s"}]
    )
    monkeypatch.setenv("LENS_API_TOKEN", "tok")
    monkeypatch.setenv("WIPO_API_KEY", "wk")
    monkeypatch.setenv("PATSNAP_API_KEY", "sk-x")
    assert main(["--epo-url", "http://e"]) == 0
    assert main(["--wipo-url", "http://w"]) == 0
    assert main(["--patsnap-url", "http://p"]) == 0
    assert main(["--lens-url", "http://l"]) == 0
    assert main(["--live-patents"]) == 0
    out = tmp_path / "p.json"
    assert main(["--lens-url", "http://l", "--output", str(out)]) == 0
    assert out.is_file()
    assert not _header("X", "")
    assert _bearer("tok") == {"Authorization": "Bearer tok"}
    assert not _bearer("")
    monkeypatch.setenv("EPO_OPS_KEY", "k")
    monkeypatch.setenv("EPO_OPS_SECRET", "s")
    monkeypatch.setattr("daedalus.cli.epo_access_token", lambda *_a, **_k: "tok")
    assert _epo_bearer_headers()["Authorization"] == "Bearer tok"
    monkeypatch.delenv("EPO_OPS_KEY")
    monkeypatch.delenv("EPO_OPS_SECRET")
    assert not _epo_bearer_headers()


def test_remaining_payload_branches() -> None:
    """Verify this behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Verify this behavior."""
        url = str(request.url)
        if "epo-dict-id" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "document-id": {
                                "country": {"$": "EP"},
                                "doc-number": {"$": "8"},
                                "kind": {"$": "A"},
                                "date": {"$": "2014"},
                            },
                            "invention-title": {
                                "empty": "",
                                "de": {"$": "Nein", "@lang": "de"},
                                "en": {"$": "QR dict title", "@lang": "en"},
                            },
                            "parties": {},
                            "classifications-cpc": {
                                "classification-cpc": {"symbol": {"$": ""}},
                            },
                        },
                        {
                            "country": "EP",
                            "doc-number": "9",
                            "kind": "A1",
                            "date": "20150601",
                            "invention-title": [
                                "",
                                {"$": "QR list title", "@lang": "en"},
                            ],
                            "inventors": [{"inventor-name": {"$": ""}}],
                        },
                        {
                            "patent_id": "EPX",
                            "title": "",
                            "publication_date": "2011-01-01",
                        },
                        {"patent_id": "EPY", "title": "No date QR"},
                        True,
                    ]
                },
            )
        if "epo-pub-obj" in url:
            return httpx.Response(200, json={"publications": {"x": 1}})
        if "wipo-list" in url:
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "WO3",
                        "title": "List QR",
                        "date": "2013-03-03",
                        "inventors": 1,
                        "ipc": "G06K",
                    }
                ],
            )
        if "wipo-int" in url:
            return httpx.Response(200, json=1)
        if "patsnap-int" in url:
            return httpx.Response(200, json=1)
        if "patsnap-skip" in url:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "results": [
                            "skip",
                            {
                                "pn": "USZ",
                                "title": "QR no date",
                            },
                            {
                                "pn": "US1",
                                "title": "QR skip mix",
                                "pbdt": None,
                                "publication_date": "2016-06-06",
                            },
                        ]
                    }
                },
            )
        if "lens-int" in url:
            return httpx.Response(200, json=1)
        if "lens-skip" in url:
            return httpx.Response(
                200,
                json={
                    "data": [
                        "skip",
                        {
                            "lens_id": "3",
                            "jurisdiction": "US",
                            "doc_number": "3",
                            "date_published": "2011-03-03",
                            "title": "QR lens mix",
                            "biblio": {
                                "invention_title": [
                                    "skip",
                                    {"text": ""},
                                    {"text": "QR lens mix"},
                                ],
                                "abstracts": [{}, {"text": "second abs"}],
                                "parties": {
                                    "inventors": [
                                        {"extracted_name": {"value": ""}},
                                        {"name": "Ada"},
                                    ]
                                },
                                "classifications_cpc": {"other": True},
                            },
                        },
                    ]
                },
            )
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    epo = fetch_epo("https://ops.example/epo-dict-id", "two_d_codes", client)
    titles = {row["title"] for row in epo}
    assert "QR dict title" in titles
    assert "QR list title" in titles
    assert not fetch_epo("https://ops.example/epo-pub-obj", "two_d_codes", client)
    wipo = fetch_wipo("https://wipo-list.test/x", "two_d_codes", client)
    assert wipo[0]["patent"] == "WO3"
    assert not fetch_wipo("https://wipo-int.test/x", "two_d_codes", client)
    assert not fetch_patsnap("https://patsnap-int.test/x", "two_d_codes", client)
    snap = fetch_patsnap("https://patsnap-skip.test/x", "two_d_codes", client)
    assert snap[0]["published_on"] == "2016-06-06"
    assert not fetch_lens("https://lens-int.test/x", "two_d_codes", client)
    lens = fetch_lens("https://lens-skip.test/x", "two_d_codes", client)
    assert lens[0]["abstract"] == "second abs"
    assert "Ada" in lens[0]["authors"]
