"""Small synthetic evidence-source response fixtures."""

PUBMED_SEARCH_RESPONSE = {
    "header": {"type": "esearch", "version": "0.3"},
    "esearchresult": {
        "count": "2",
        "retmax": "2",
        "retstart": "0",
        "idlist": ["11111111", "22222222"],
    },
}

PUBMED_FETCH_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">11111111</PMID>
      <Article>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2024</Year><Month>06</Month><Day>01</Day></PubDate>
          </JournalIssue>
          <Title>Synthetic Ophthalmology Journal</Title>
        </Journal>
        <ArticleTitle>Comparative treatment for neovascular macular degeneration</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Synthetic fixture background.</AbstractText>
          <AbstractText Label="RESULTS">No clinical conclusion is asserted.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><ForeName>Ada</ForeName><LastName>Example</LastName></Author>
          <Author><CollectiveName>Fixture Study Group</CollectiveName></Author>
        </AuthorList>
        <Language>eng</Language>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
      <CommentsCorrectionsList>
        <CommentsCorrections RefType="CorrectedandRepublishedFrom">
          <RefSource>Synthetic prior record</RefSource>
        </CommentsCorrections>
      </CommentsCorrectionsList>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Macular Degeneration</DescriptorName></MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">11111111</ArticleId>
        <ArticleId IdType="doi">10.0000/synthetic.1</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">22222222</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><MedlineDate>2023 Winter</MedlineDate></PubDate></JournalIssue>
          <Title>Synthetic Safety Journal</Title>
        </Journal>
        <ArticleTitle>Retracted synthetic comparison</ArticleTitle>
        <AuthorList><Author><ForeName>Test</ForeName><LastName>Author</LastName></Author></AuthorList>
        <Language>eng</Language>
        <PublicationTypeList>
          <PublicationType>Retracted Publication</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList><ArticleId IdType="pubmed">22222222</ArticleId></ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

CLINICAL_TRIALS_RESPONSE = {
    "totalCount": 2,
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000001",
                    "briefTitle": "Synthetic comparative retinal trial",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "startDateStruct": {"date": "2022-01"},
                    "completionDateStruct": {"date": "2024-06-30"},
                    "lastUpdatePostDateStruct": {"date": "2025-01-15"},
                },
                "sponsorCollaboratorsModule": {
                    "leadSponsor": {"name": "Synthetic Academic Center"}
                },
                "descriptionModule": {
                    "briefSummary": "A synthetic fixture; it contains no study findings."
                },
                "conditionsModule": {
                    "conditions": ["Neovascular age-related macular degeneration"]
                },
                "designModule": {
                    "studyType": "INTERVENTIONAL",
                    "phases": ["PHASE3"],
                    "designInfo": {"allocation": "RANDOMIZED"},
                    "enrollmentInfo": {"count": 120, "type": "ACTUAL"},
                },
                "armsInterventionsModule": {
                    "interventions": [
                        {"type": "DRUG", "name": "Aflibercept"},
                        {"type": "DRUG", "name": "Ranibizumab"},
                    ]
                },
                "outcomesModule": {
                    "primaryOutcomes": [{"measure": "Change in visual acuity"}],
                    "secondaryOutcomes": [{"measure": "Adverse events"}],
                },
                "contactsLocationsModule": {
                    "locations": [
                        {
                            "facility": "Synthetic Eye Center",
                            "city": "Example City",
                            "state": "Illinois",
                            "country": "United States",
                        }
                    ]
                },
            },
            "hasResults": True,
        }
    ],
    "nextPageToken": "synthetic-next-page",
}

CARDIOMETABOLIC_PUBMED_SEARCH_RESPONSE = {
    "header": {"type": "esearch", "version": "0.3"},
    "esearchresult": {
        "count": "1",
        "retmax": "1",
        "retstart": "0",
        "idlist": ["33333333"],
    },
}

CARDIOMETABOLIC_PUBMED_FETCH_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">33333333</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
          <Title>Synthetic Cardiometabolic Journal</Title>
        </Journal>
        <ArticleTitle>Synthetic direct cardiometabolic comparison</ArticleTitle>
        <Abstract>
          <AbstractText>
            Semaglutide, empagliflozin, and HbA1c appear only as synthetic
            ranking terms. No clinical result is asserted.
          </AbstractText>
        </Abstract>
        <Language>eng</Language>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList><ArticleId IdType="pubmed">33333333</ArticleId></ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

CARDIOMETABOLIC_CLINICAL_TRIALS_RESPONSE = {
    "totalCount": 1,
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000002",
                    "briefTitle": "Synthetic direct cardiometabolic trial",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "startDateStruct": {"date": "2024-01"},
                    "completionDateStruct": {"date": "2025-01"},
                    "lastUpdatePostDateStruct": {"date": "2025-02"},
                },
                "designModule": {
                    "studyType": "INTERVENTIONAL",
                    "phases": ["PHASE3"],
                    "designInfo": {"allocation": "RANDOMIZED"},
                    "enrollmentInfo": {"count": 100, "type": "ACTUAL"},
                },
                "conditionsModule": {"conditions": ["Type 2 diabetes mellitus"]},
                "armsInterventionsModule": {
                    "interventions": [
                        {"type": "DRUG", "name": "Semaglutide"},
                        {"type": "DRUG", "name": "Empagliflozin"},
                    ]
                },
                "outcomesModule": {"primaryOutcomes": [{"measure": "Synthetic HbA1c outcome"}]},
            },
            "hasResults": True,
        }
    ],
}

RARE_DISEASE_PUBMED_SEARCH_RESPONSE = {
    "header": {"type": "esearch", "version": "0.3"},
    "esearchresult": {
        "count": "1",
        "retmax": "1",
        "retstart": "0",
        "idlist": ["44444444"],
    },
}

RARE_DISEASE_PUBMED_FETCH_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">44444444</PMID>
      <Article>
        <Journal>
          <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
          <Title>Synthetic Neuromuscular Journal</Title>
        </Journal>
        <ArticleTitle>Synthetic rare-disease treatment comparison</ArticleTitle>
        <Abstract>
          <AbstractText>
            Efgartigimod, rozanolixizumab, and MG-ADL appear only as synthetic
            ranking terms. No clinical result is asserted.
          </AbstractText>
        </Abstract>
        <Language>eng</Language>
        <PublicationTypeList>
          <PublicationType>Systematic Review</PublicationType>
        </PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList><ArticleId IdType="pubmed">44444444</ArticleId></ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

RARE_DISEASE_CLINICAL_TRIALS_RESPONSE = {
    "totalCount": 2,
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000003",
                    "briefTitle": "Synthetic efgartigimod trial",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "startDateStruct": {"date": "2023-01"},
                    "completionDateStruct": {"date": "2024-01"},
                    "lastUpdatePostDateStruct": {"date": "2024-02"},
                },
                "designModule": {
                    "studyType": "INTERVENTIONAL",
                    "phases": ["PHASE3"],
                    "designInfo": {"allocation": "RANDOMIZED"},
                    "enrollmentInfo": {"count": 75, "type": "ACTUAL"},
                },
                "conditionsModule": {"conditions": ["Myasthenia gravis"]},
                "armsInterventionsModule": {
                    "interventions": [{"type": "DRUG", "name": "Efgartigimod"}]
                },
                "outcomesModule": {"primaryOutcomes": [{"measure": "Synthetic MG-ADL outcome"}]},
            },
            "hasResults": True,
        },
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT00000004",
                    "briefTitle": "Synthetic rozanolixizumab trial",
                },
                "statusModule": {
                    "overallStatus": "COMPLETED",
                    "startDateStruct": {"date": "2023-02"},
                    "completionDateStruct": {"date": "2024-02"},
                    "lastUpdatePostDateStruct": {"date": "2024-03"},
                },
                "designModule": {
                    "studyType": "INTERVENTIONAL",
                    "phases": ["PHASE3"],
                    "designInfo": {"allocation": "RANDOMIZED"},
                    "enrollmentInfo": {"count": 80, "type": "ACTUAL"},
                },
                "conditionsModule": {"conditions": ["Myasthenia gravis"]},
                "armsInterventionsModule": {
                    "interventions": [{"type": "DRUG", "name": "Rozanolixizumab"}]
                },
                "outcomesModule": {"primaryOutcomes": [{"measure": "Synthetic MG-ADL outcome"}]},
            },
            "hasResults": True,
        },
    ],
}
