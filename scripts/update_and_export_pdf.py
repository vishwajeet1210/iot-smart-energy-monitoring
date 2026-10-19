import os
import sys
import time
import win32com.client

def update_and_export():
    current_dir = os.path.abspath(os.getcwd())
    docx_path = os.path.join(current_dir, "REPORT_MATERIALS", "files", "DevSecOps_CIAP_Report_Smart_Energy_Monitor.docx")
    pdf_path = os.path.join(current_dir, "REPORT_MATERIALS", "files", "DevSecOps_CIAP_Report_Smart_Energy_Monitor.pdf")

    print(f"Target DOCX: {docx_path}")
    print(f"Target PDF:  {pdf_path}")

    if not os.path.exists(docx_path):
        print(f"Error: DOCX not found at {docx_path}")
        return False

    print("Launching Microsoft Word via COM...")
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0  # wdAlertsNone

    try:
        print("Opening document in Word...")
        doc = word.Documents.Open(docx_path)

        print("Updating Table of Contents and document fields...")
        try:
            # Update all TOCs
            for toc in doc.TablesOfContents:
                toc.Update()
                print("TOC updated.")
        except Exception as e_toc:
            print(f"Warning on TOC update: {e_toc}")

        try:
            # Update all fields in main document story
            for field in doc.Fields:
                field.Update()
            print("Document fields updated.")
        except Exception as e_fld:
            print(f"Warning on field update: {e_fld}")

        print("Saving updated DOCX...")
        doc.Save()
        print("DOCX saved.")

        print("Exporting PDF (wdFormatPDF / ExportAsFixedFormat)...")
        # wdExportFormatPDF = 17
        doc.ExportAsFixedFormat(
            OutputFileName=pdf_path,
            ExportFormat=17,
            OpenAfterExport=False,
            OptimizeFor=0, # wdExportOptimizeForPrint
            CreateBookmarks=1, # wdExportCreateHeadingBookmarks
            DocStructureTags=True
        )
        print("PDF successfully exported.")
        return True

    except Exception as e:
        print(f"Error during Word automation: {e}")
        return False
    finally:
        try:
            doc.Close(SaveChanges=-1) # wdSaveChanges
        except:
            pass
        try:
            word.Quit()
        except:
            pass
        print("Word application terminated cleanly.")

if __name__ == "__main__":
    success = update_and_export()
    if not success:
        sys.exit(1)
