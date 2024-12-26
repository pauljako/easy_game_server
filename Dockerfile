FROM python

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME [ "/usr/src/app/data" ]

EXPOSE 6500

CMD [ "python", "./main.py" ]
