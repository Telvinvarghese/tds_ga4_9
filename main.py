import re
import io
import pdfplumber
import pandas as pd
from fastapi import FastAPI, UploadFile
from mangum import Mangum

app = FastAPI()

@app.post("/process-pdf")
async def GA4_9_with_pdfplumber(question: str, file: UploadFile):
    match = re.search(
        r"What is the total (.+?) marks of students who scored (\d+) or more marks in (.+?) in groups (\d+)-(\d+) \(including both groups\)\?",
        question.strip()
    )

    if not match:
        return {"error": "Question format is incorrect"}

    final_subject, min_score, subject, min_group, max_group = match.groups()
    min_score, min_group, max_group = map(int, (min_score, min_group, max_group))

    print("Params:", final_subject, min_score, subject, min_group, max_group)

    df_list = []
    with pdfplumber.open(file.file) as pdf_reader:
        total_pages = len(pdf_reader.pages)
        min_group = max(0, min_group - 1)  
        max_group = min(max_group, total_pages)  

        for i in range(min_group, max_group):
            page = pdf_reader.pages[i]
            tables = page.extract_tables()
            for table in tables:
                df_list.append(pd.DataFrame(table[1:], columns=table[0]))

    if not df_list:
        return {"error": "No tables found in the specified pages"}

    df = pd.concat(df_list, ignore_index=True)

    if subject not in df.columns or final_subject not in df.columns:
        return {"error": f"Required columns '{subject}' or '{final_subject}' not found in extracted data"}

    df[subject] = pd.to_numeric(df[subject], errors="coerce")
    df[final_subject] = pd.to_numeric(df[final_subject], errors="coerce")

    result = df[df[subject] >= min_score][final_subject].sum()

    return {"total_marks": result}

handler = Mangum(app)  # Required for Vercel
