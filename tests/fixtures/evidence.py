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
