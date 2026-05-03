"""
情感分析脚本
使用TextBlob对文本进行情感分析，按换行符拆分句子
输出: Sentence_Index, Polarity, Subjectivity
"""

from textblob import TextBlob
import csv

# 读取文本文件
with open('pome1.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 按换行符拆分句子（过滤掉空行）
lines = [line.strip() for line in text.split('\n') if line.strip()]

# 情感分析结果
results = []

for i, line in enumerate(lines, 1):
    blob = TextBlob(line)
    polarity = blob.sentiment.polarity  # -1 到 1
    subjectivity = blob.sentiment.subjectivity  # 0 到 1

    results.append({
        'Sentence_Index': i,
        'Polarity': round(polarity, 4),
        'Subjectivity': round(subjectivity, 4)
    })

    print(f"Line {i}: {line[:50]}...")
    print(f"  Polarity: {polarity:.4f}, Subjectivity: {subjectivity:.4f}\n")

# 导出CSV
output_file = 'sentiment_analysis_result.csv'
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['Sentence_Index', 'Polarity', 'Subjectivity'])
    writer.writeheader()
    writer.writerows(results)

print(f"结果已导出到: {output_file}")