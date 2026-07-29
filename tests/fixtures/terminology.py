ICD_RESPONSE = [
    8,
    ["H35.3211", "H35.3221", "H35.3231", "H35.3291"],
    None,
    [
        [
            "H35.3211",
            "Exudative age-related macular degeneration, right eye, "
            "with active choroidal neovascularization",
        ],
        [
            "H35.3221",
            "Exudative age-related macular degeneration, left eye, "
            "with active choroidal neovascularization",
        ],
        [
            "H35.3231",
            "Exudative age-related macular degeneration, bilateral, "
            "with active choroidal neovascularization",
        ],
        [
            "H35.3291",
            "Exudative age-related macular degeneration, unspecified eye, "
            "with active choroidal neovascularization",
        ],
    ],
]

CARDIOMETABOLIC_ICD_RESPONSE = [
    2,
    ["E11.9", "E11.A"],
    None,
    [
        ["E11.9", "Type 2 diabetes mellitus without complications"],
        ["E11.A", "Type 2 diabetes mellitus without complications in remission"],
    ],
]

RARE_DISEASE_ICD_RESPONSE = [
    1,
    ["G70.00"],
    None,
    [["G70.00", "Myasthenia gravis without (acute) exacerbation"]],
]


def rx_response(*, rxcui: str, name: str, score: str) -> dict[str, object]:
    return {
        "approximateGroup": {
            "candidate": [
                {
                    "rxcui": rxcui,
                    "rxaui": "1",
                    "score": score,
                    "rank": "1",
                    "name": name,
                    "source": "RXNORM",
                }
            ]
        }
    }
