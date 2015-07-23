import csv
import math

result = {}

with open('profile.log', 'rb') as profile_log:
    reader = csv.reader(profile_log)
    for row in reader:
        if(len(row) == 1):
            if(row[0].startswith("site: ")):
                current = []
                print row[0][6:]
                result[row[0][5:]] = current
        elif(len(row) >= 4 and len(row) <= 7):
            crawler_download = row[0]
            crawler_parse = row[1]
            crawler_total = row[2]
            article_parse = ""
            article_db = ""
            article_warc = ""
            article_total = row[-1]
            if(len(row) >= 5):
                article_parse = row[3]
            if(len(row) == 7):
                article_db = row[4]
                article_warc = row[5]


            current.append({"crawler_download":crawler_download,
                            "crawler_parse": crawler_parse,
                            "crawler_total": crawler_total,
                            "article_parse":article_parse,
                            "article_db":article_db,
                            "article_warc":article_warc,
                            "article_total":article_total})
        else:
            print

for site,rows in result.iteritems():
    with open(site + ".csv", 'wb') as csvfile:
        writer = csv.writer(csvfile)
        columns = ["crawler_download", "crawler_parse", "crawler_total", "article_parse", "article_db", "article_warc", "article_total"]
        writer.writerow(columns)
        for row in rows:
            csv_row = []
            for c in columns:
                csv_row.append(row[c])
            writer.writerow(csv_row)
