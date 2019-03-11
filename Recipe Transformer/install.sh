printf "Install all the libraries/dependencies used in this project...\n"
pip3 install -r requirements.txt

printf "\nDownload the spaCy language model used in this project...\n"
python3 -m spacy download en

printf "\nInstall NLTK packages used, such as 'punkt'...\n"
python3 -m nltk.downloader all
