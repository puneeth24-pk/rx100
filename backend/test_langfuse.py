import traceback
try:
    print("Importing langfuse...")
    import langfuse
    print("langfuse imported successfully")
except Exception:
    with open('langfuse_error.txt', 'w') as f:
        f.write(traceback.format_exc())
    print("Error saved to langfuse_error.txt")
