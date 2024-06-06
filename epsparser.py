import os
import csv
from bs4 import BeautifulSoup
import re
import pandas as pd

# Code to design a parser that extracts Earnings Per Share from Financial Documents (10-K,10-Q)

def parse_html(html):
    with open(html, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    eps_values = {}

    # Regex patterns to identify EPS (basic handles the bulk of the work, greedy matched as little as possible)
    restriction_pattern = r'[^,.;]{5,50}?' #Restriction pattern in order allow for characters following 'e.g. attributed to x company shareholders' but still restrict greediness
    patterns = {
        'basic': re.compile(rf'(?<!non-GAAP\s)(\$(\d+\.\d+)\s+)?(Basic\s+(?:and diluted\s+)?(?:GAAP\s+)?(Earnings|Net\s+(?:\(loss\)\s+)?Income|Net\s+Earnings|Income)\s+(?:\(loss\)\s+)?per\s+(common|ordinary)?\s*share)|(Earnings|Net\s+Income|Net\s+Earnings|Income|Loss)\s+(\(loss\)\s+)?(attributable\s*to {restriction_pattern}|allocated\s*to {restriction_pattern}|available\s*to {restriction_pattern})?per\s+(common|ordinary)?\s*share\s*(attributable\s*to {restriction_pattern}|allocated\s*to {restriction_pattern})?\s*(:|-|—)?\s*Basic', re.I),
        'diluted': re.compile(r'(\$(\d+\.\d+)\s+)?(Diluted\s+(Earnings|Net\s+Income|Net\s+Earnings)\s+(?:\(loss\)\s+)?per\s+(?:common\s+)?share)|(Earnings|Net\s+Income|Net\s+Earnings)\s+(\(loss\)\s+)?per\s+(common\s+)?share.*?Diluted', re.I),
        'loss': re.compile(r'(\$(\d+\.\d+)\s+)?(\((Loss)\)\s+earnings\s+per\s+share)|(\(net\)\s+)?Loss\s+per\s+(?:common\s+)?share', re.I),
        'per_share_first': re.compile(rf'per\s+(?:common\s+)?share\s*(data:)?\s*(Earnings|Net\s+(?:\(loss\)\s+)?Income|Net\s+(?:\(loss\)\s+)?Earnings|Income)\s*(:|-|—)?\s*Basic',re.I)
    }
    # Normalized using get_text but also attempted using soup's parse tree, which felt ineffective due to inconsistent html formatting
    text = soup.get_text()

    # Extracting value from matches
    for key, pattern in patterns.items():
        match = pattern.search(text)
        if match:
            text_slice = text[match.start():match.end()+100]
            number_match = re.search(r'(\()?(\d+\.\d+)\s*(\))?', text_slice)
            if number_match:
                value = float(number_match.group(2))
                if number_match.group(1) and number_match.group(3):
                    value = -value
                elif key=='loss':
                    value = -value
                eps_values[key] = value

    # Value prioritization logic 
    prioritization_order = ['basic','loss', 'diluted','per_share_first']
    for priority in prioritization_order:
        if priority in eps_values:
            return eps_values[priority]

# Functions needed to run parser
def parse_folder(folder):
    results = []
    for file in os.listdir(folder):
        file_path = os.path.join(folder,file)
        eps = parse_html(file_path)
        results.append((file,eps))
    return results

def write_results(results,output):
    with open(output,'w',newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['filename','EPS'])
        for result in results:
            writer.writerow(result)

def run_test(output,correct_output):
    output_csv = pd.read_csv(output)
    correct_csv = pd.read_csv(correct_output)
    correct_count = 0
    for ((index1, row1), (index2, row2)) in zip(output_csv.iterrows(), correct_csv.iterrows()):
        # Compare the EPS values; considering a small float precision tolerance might be necessary depending on the data
        if abs(row1['EPS'] - row2['EPS']) < 0.001:
            correct_count += 1
        else:
            print(f"Mismatch found: {row1['filename']} - Output: {row1['EPS']}, Correct: {row2['EPS']}")
    total = len(output_csv)
    accuracy = (correct_count / total) * 100 if total > 0 else 0
    print(f"Total files: {total}, Correctly matched EPS: {correct_count}, Accuracy: {accuracy:.2f}%")

folder_path = 'Training_Filings'
output_csv_file = 'EPS_Results.csv'
correct_csv = 'correct_results.csv'

results = parse_folder(folder_path)
write_results(results, output_csv_file)
run_test('EPS_Results.csv',correct_csv)