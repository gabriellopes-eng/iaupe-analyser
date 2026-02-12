from src.deepseek_client import analyze_target_audience

if __name__ == "__main__":
    sample_text = "Edital destinado a pesquisadores doutores vinculados a instituições públicas brasileiras."
    result = analyze_target_audience(sample_text)
    print(result)