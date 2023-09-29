#!/usr/bin/env python3
import argparse
from Bio import Entrez
import concurrent.futures
from habanero import crossref
import itertools
import pdfkit
import markdown2
import os
import textwrap

def get_doi(record):
    doi_loc = record['PubmedArticle'][0]['MedlineCitation']['Article']['ELocationID']
    if len(doi_loc) > 1 or isinstance(doi_loc, str):
        DOI = doi_loc[1].split(",")[0]
    elif len(doi_loc) <= 1:
        DOI = doi_loc[0].split(",")[0]
    URL = f"https://doi.org/{DOI}"
    return DOI, URL

def get_authors(record):
    name_list = []
    for alist in record['PubmedArticle'][0]['MedlineCitation']['Article']['AuthorList']:
        if len(alist.keys()) == 5:
            last_name = alist["LastName"]
            first_name = alist["ForeName"]
            name_list.append(f"{first_name} {last_name}")
    author_list = " and ".join(name_list)
    return author_list

def get_keywords(record):
    keyword_list = []
    for keyword in record['PubmedArticle'][0]['MedlineCitation']['KeywordList']:
        if isinstance(keyword, list):
            keyword_list.extend(keyword)
        else:
            keyword_list.append(keyword)
    keywords = ";".join(keyword_list)
    return keywords

def get_pmid(record):
    pmid = record['PubmedArticle'][0]['MedlineCitation']['PMID'].split(",")[0]
    return pmid

def get_others(record):
    article = record['PubmedArticle'][0]['MedlineCitation']['Article']
    title = article['ArticleTitle']
    journal = article['Journal']['Title']
    abstract = article['Abstract']['AbstractText'][0]
    year = article['Journal']['JournalIssue']['PubDate']['Year']
    month = article['Journal']['JournalIssue']['PubDate'].get('Month', '')
    if 'Volume' in article['Journal']['JournalIssue'].keys():
        volume = article['Journal']['JournalIssue']['Volume']
    else:
        volume = ''
    if 'Issue' in article['Journal']['JournalIssue'].keys():
        issue = article['Journal']['JournalIssue']['Issue']
    else:
        issue = ''
    if 'Pagination' in article.keys():
        pages = article['Pagination'].get('MedlinePgn', '')
    else:
        pages = ''
    return title, journal, abstract, year, month, pages,volume, issue,

def old_get_others(record):
    tmp_dict = record['PubmedArticle'][0]['MedlineCitation']['Article']
    date_dict = tmp_dict['Journal']['JournalIssue']
    title = tmp_dict['ArticleTitle']
    journal = tmp_dict['Journal']['Title']
    abstract = tmp_dict['Abstract']['AbstractText'][0]
    pages = tmp_dict['Pagination']['MedlinePgn']
    volume = date_dict['Volume']
    issue = date_dict['Issue']
    year = date_dict['PubDate']['Year']
    month = date_dict['PubDate']['Month']
    return title, journal, abstract, year, month, volume, issue, pages

def get_pubtype(record):
    j_type = record['PubmedArticle'][0]['MedlineCitation']['Article']['PublicationTypeList'][0].split(",")[0]
    return j_type

def bibtex(bibtex_cat, bibtex_id, doi, url, pmid, year, month, author, title, journal, volume, issue, pages, keywords, abstract):
    bibtex_item = textwrap.dedent(r"""
    {BIBCAT}{{{BIBID},
        doi = {DOI},
        pmid = {PMID},                             
        url = {URL},
        year = {YEAR},
        month = {MONTH},
        author = {AUTHOR},
        title = {TITLE},
        journal = {JOURNAL},
        volume = {VOLUME},
        number = {ISSUE},
        pages = {PAGES},
        keywords = {KEYWORDS},
        abstract = {ABSTRACT}
    }}
    """.format(BIBCAT=bibtex_cat, BIBID=bibtex_id, DOI=doi, URL=url, PMID=pmid, YEAR=year, MONTH=month, AUTHOR=author, TITLE=title, JOURNAL=journal, VOLUME=volume, ISSUE=issue, PAGES=pages, KEYWORDS=keywords, ABSTRACT=abstract))
    return bibtex_item

def abs_block(title, author, year, journal, url, keywords, abstract):
    authors = author.split(" and ")[0].split(" ")[1] + " et al." + " ." + year + "." + journal
    block = textwrap.dedent(r"""
    * {TITLE}
    ** Keywords:
        - {KEYWORDS}
    *** Authors:
        - {AUTHOR}                            
    **** URL:
        - [{URL}](URL)
    
    {ABSTRACT}
    """.format(TITLE=title, AUTHOR=authors, YEAR=year, JOURNAL=journal, URL=url, KEYWORDS=keywords, ABSTRACT=abstract))
    block = block.replace("*", "#")
    return block

def convert_markdown(input_md, out_html, out_pdf):
    # Convert markdown to HTML
    with open(input_md, 'r') as f:
        html = markdown2.markdown(f.read())
    with open(out_html, 'w') as f:
        f.write(html)
    # Convert HTML to PDF
    pdfkit.from_file(out_html, out_pdf)

def arg_parser():
    parser = argparse.ArgumentParser(description='Download 16s sequences from NCBI')
    parser.add_argument('-a', '--abstract_file', help='Path to file to write journal article abstracts', default = 'abstracts.md')
    parser.add_argument('-b', '--bibtex_file', help='Path to file to write journal article bibtex', default = 'bibtex.bib')
    parser.add_argument('-t', '--term', type=str, help='Search term', required=True)
    parser.add_argument('--api', type=str, help='NCBI API key', default = os.getenv("NCBI_API_KEY"))
    parser.add_argument('--email', type=str, help='Email address', default = os.getenv("NCBI_EMAIL"))
    parser.add_argument('--ncpu', type=int, help='Number of CPUs to use', default = os.cpu_count())
    return parser.parse_args()

def slice_dict(in_dict, batch_size):
    import itertools
    batches = [dict(itertools.islice(in_dict.items(), i, i + batch_size)) for i in range(0, len(in_dict), batch_size)]
    return batches

def search_articles(TERM, email, api):
    Entrez.email = email
    handle = Entrez.esearch(db="pubmed", term=TERM, api_key=api, retmax='10000000')
    record = Entrez.read(handle)
    return record["IdList"]

def sort_articles(rec_id, email, api):
    rec_dict = {}
    Entrez.email = email
    for id in rec_id:
        rec = Entrez.read(Entrez.efetch(db="pubmed", id=id, api_key=api))
        try:
            j_type = rec['PubmedArticle'][0]['MedlineCitation']['Article']['PublicationTypeList'][0].split(",")[0]
            if j_type in ['Journal Article', 'Review', 'Meta-Analysis', 'Letter']:
                rec_dict[id] = rec
        except IndexError:
            continue
    return rec_dict

def build_abs(records):
    abstract_list = []
    for key in records.keys():
        record = records[key]
        #for record in records:
        _, url = get_doi(record)
        authors = get_authors(record)
        keywords = get_keywords(record)
        title, journal, abstract, year, _, _, _, _ = get_others(record)
        abstract_list.append(abs_block(title, authors, year, journal, url, keywords, abstract))
    return abstract_list

def build_bibtex(records):
    bibtex_list = []
    for key in records.keys():
        record = records[key]
    #for record in records:
        doi, url = get_doi(record)
        authors = get_authors(record)
        keywords = get_keywords(record)
        title, journal, abstract, year, month, volume, issue, pages = get_others(record)
        bibtex_key = f"{authors.split(' and ')[0]}{year}"
        pmid = get_pmid(record)
        pubtype = get_pubtype(record)
        if pubtype == "Journal Article":
            bibcat = "@article"
        elif pubtype == "Review":
            bibcat = "@review"
        elif pubtype == "Meta-Analysis":
            bibcat = "@meta-analysis"
        elif pubtype == "Letter":
            bibcat = "@letter"
        bibtex_list.append(bibtex(bibcat, bibtex_key, doi, url, pmid, year, month, authors, title, journal, volume, issue, pages, keywords, abstract))
    return bibtex_list

def make_files(input_md):
    file_dir = os.path.dirname(input_md)
    file_name = os.path.basename(input_md)
    file_base = os.path.splitext(file_name)[0]
    out_html = os.path.join(file_dir, f"{file_base}.html")
    out_pdf = os.path.join(file_dir, f"{file_base}.pdf")
    convert_markdown(input_md, out_html, out_pdf)

def main():
    args = arg_parser()
    search_results = search_articles(args.term, args.email, args.api)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.ncpu) as executor:
        batches = [search_results[i:i+50] for i in range(0, len(search_results), 50)]
        futures = [executor.submit(sort_articles, batch, args.email, args.api) for batch in batches]
        concurrent.futures.wait(futures)
        # Combine the results
        rec_res = {}
        for future in futures:
            result = future.result()
            rec_res.update(result)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.ncpu // 2) as executor:
        dict_batches = [dict(itertools.islice(rec_res.items(), i, i + 50)) for i in range(0, len(rec_res), 50)]
        #dict_batches = [rec_res[i:i+50] for i in range(0, len(rec_res), 50)]
        futures1 = [executor.submit(build_abs, batch) for batch in dict_batches]
        futures2 = [executor.submit(build_bibtex, batch) for batch in dict_batches]
        concurrent.futures.wait(futures1)
        concurrent.futures.wait(futures2)
        # Combine the results
        abs_res = []
        for future in futures1:
            result = future.result()
            abs_res.extend(result)
        # Combine the results
        bib_res = []
        for future in futures2:
            result = future.result()
            bib_res.extend(result)
    
    with open(args.abstract_file, 'w') as f:
        for item in abs_res:
            if item is not None:
                f.write(item)
        #f.write('\n'.join(abs_res))
    
    with open(args.bibtex_file, 'w') as f:
        for item in bib_res:
            if item is not None:
                f.write(item)
        #f.write('\n'.join(bib_res))

    make_files(args.abstract_file)

if __name__ == '__main__':
    main()