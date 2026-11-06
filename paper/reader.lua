-- Web reader only (scripts/build_web_paper.py): put the bibliography where the \bibliography command stands, before
-- the appendices as in the PDF, instead of at the end of the document where citeproc would put it by default.
function Para(el)
  if #el.content == 1 and el.content[1].text == "REFERENCES-GO-HERE" then
    return pandoc.Div({}, pandoc.Attr("refs"))
  end
end
