def get_doi(record):
    if len(record['PubmedArticle'][0]['MedlineCitation']['Article']['ELocationID']) > 1:
        DOI = record['PubmedArticle'][0]['MedlineCitation']['Article']['ELocationID'][1]
    elif len(record['PubmedArticle'][0]['MedlineCitation']['Article']['ELocationID']) <= 1:
        DOI = record['PubmedArticle'][0]['MedlineCitation']['Article']['ELocationID'][0]
    URL = f"https://doi.org/{DOI}"
    return DOI, URL

def get_authors(record):
    name_list = []
    for alist in len(record['PubmedArticle'][0]['MedlineCitation']['Article']['AuthorList']):
        if len(alist.keys()) == 5:
            last_name = alist["LastName"]
            first_name = alist["ForeName"]
            name_list.append(f"{first_name} {last_name}")
    author_list = " and ".join(name_list)
    return author_list

def get_keywords(record):
    keyword_list = []
    for keyword in record['PubmedArticle'][0]['MedlineCitation']['KeywordList']:
        keyword_list.append(keyword)
    keywords = ";".join(keyword_list)
    return keywords

def get_pmid(record):
    pmid = record['PubmedArticle'][0]['MedlineCitation']['PMID'].split(",")[0]
    return pmid

def get_others(record):
    tmp_dict = record['PubmedArticle'][0]['MedlineCitation']['Article']
    title = ['ArticleTitle']
    journal = tmp_dict['Journal']['Title']
    abstract = tmp_dict['Abstract']['AbstractText'][0]
    pages = tmp_dict['Pagination']['MedlinePgn']
    for key in tmp_dict['Journal']['JournalIssue'].keys():
        if key == "Volume":
            volume = tmp_dict[key]
        elif key == "Issue":
            issue = tmp_dict[key]
        elif key == "PubDate":
            year = tmp_dict[key]["Year"]
            month = tmp_dict[key]["Month"]
    return title, journal, abstract, year, month, volume, issue, pages

def get_pubtype(record):
    j_type = record['PubmedArticle'][0]['MedlineCitation']['Article']['PublicationTypeList'][0].split(",")[0]
    return j_type

def bibtex(bibtex_cat, bibtex_id, doi, url, pmid, year, author, title, journal, volume, issue, pages, keywords, abstract):
    import textwrap
    bibtex_item = textwrap.dedent(r"""
    @{BIBCAT}{{BIBID},
        doi = {DOI},
        pmid = {PMID},                             
        url = {URL},
        year = {YEAR},
        author = {AUTHOR},
        title = {TITLE},
        journal = {JOURNAL},
        volume = {VOLUME},
        number = {ISSUE},
        pages = {PAGES},
        keywords = {KEYWORDS},
        abstract = {ABSTRACT}
    }
    """.format(BIBCAT=bibtex_cat, BIBID=bibtex_id, DOI=doi, URL=url, PMID=pmid, YEAR=year, AUTHOR=author, TITLE=title, JOURNAL=journal, VOLUME=volume, ISSUE=issue, PAGES=pages, KEYWORDS=keywords, ABSTRACT=abstract))
    return bibtex_item

def abs_block(title, author, year, journal, url, keywords, abstract):
    import textwrap
    textwrap.dedent(r"""
    \# {TITLE}
    \#\# {KEYWORDS}
    \#\#\# {AUTHOR} 
    \#\#\# {YEAR};{JOURNAL} 
    \#\#\# {URL}
    
    {ABSTRACT}
    """.format(TITLE=title, AUTHOR=author, YEAR=year, JOURNAL=journal, URL=url, KEYWORDS=keywords, ABSTRACT=abstract))