import pandas as pd
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pickle
import sklearn
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
import warnings

warnings.filterwarnings('ignore')


def transform(df):
    df.dropna(inplace=True)
    df['Массовый'] = df['content'].str.contains('массов')
    df['Жалуются'] = df['content'].str.contains('жалу')
    df['Нарушения'] = df['content'].str.contains('Наруш')
    df['Незаконно'] = df['content'].str.contains('Незакон')
    df['Жалоба'] = df['content'].str.contains('жалоб')
    df['Утечка'] = df['content'].str.contains('утечк')
    df['возбудили'] = df['content'].str.contains('возбудил')
    df['Ущерб'] = df['content'].str.contains('ущерб')
    df['Убытки'] = df['content'].str.contains('убыт')
    df['Утечка'] = df['content'].str.contains('вред')
    df['Авария'] = df['content'].str.contains('авари')
    df['Сбой'] = df['content'].str.contains('сбой')
    df['Приостановили'] = df['content'].str.contains('приостан')
    df['Роспотребнадзор'] = df['content'].str.contains('Роспотребнадзор')
    df['Роскомнадзор'] = df['content'].str.contains('Роскомнадзор')
    return df


def test():
    df = pd.read_csv('/Users/pomidorka/Desktop/prog/class/news.csv', sep=';')
    df = transform(df)
    vect1, vect2, pickled_model4 = pickle.load(
        open('/Users/pomidorka/Desktop/prog/class/model_end_with_vect5.pkl', 'rb'))
    X = df.iloc[:, :].values
    X3 = vect1.transform(X[:, 0]).todense()
    X4 = vect2.transform(X[:, 1]).todense()
    X_mat = np.hstack((X3, X4))
    df3 = df.iloc[:, 2:15]
    df3_matrix = np.matrix(df3)
    X_mat2 = np.hstack((X_mat, df3))
    X_array = np.squeeze(np.asarray(X_mat2))
    y_pred = pickled_model4.predict(X_array)

    # Обрабатываем результат прогноза

    y_pred2 = pd.Series(y_pred)
    result = pd.concat([df['title'], y_pred2], axis=1)
    result.dropna(inplace=True)
    total = result[result[0] == 1]
    html_table = total.to_html()

    # отправляем результат на почту
    msg = MIMEMultipart()
    message = 'Report'

    # setup the parameters of the message
    password = "JhfswQ23idYvryt8N1jZ"
    msg['From'] = "mark.ii24@mail.ru"
    msg['To'] = "granbysur@gmail.com"
    msg['Subject'] = "Отчет"

    # add in the message body
    html_table = MIMEText(html_table, 'html')
    msg.attach(html_table)

    # create server
    server = smtplib.SMTP('smtp.mail.ru: 587')

    server.starttls()

    # Login Credentials for sending the mail
    server.login(msg['From'], password)

    # send the message via the server.
    server.send_message(msg)

    server.quit()

    print("successfully sent email to %s:" % (msg['To']))
