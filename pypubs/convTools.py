def convert_markdown(input_md, out_html, out_pdf):
    import markdown2
    import pdfkit
    # Convert markdown to HTML
    with open(input_md, 'r') as f:
        html = markdown2.markdown(f.read())
    with open(out_html, 'w') as f:
        f.write(html)
    # Convert HTML to PDF
    pdfkit.from_file(out_html, out_pdf)