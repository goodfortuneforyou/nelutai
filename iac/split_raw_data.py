import pandas as pd
import os
import shutil
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
from langchain_openai import AzureOpenAIEmbeddings
from unidecode import unidecode

docs_filtered_path = os.environ.get('FILTERED_PATH', 'filtered')
index_path = 'index'
raw_data_path = os.environ.get('RAW_DATA_PATH', 'raw_data.csv')
deployment = os.environ['AZURE_OPENAI_DEPLOYMENT_NAME']
api_version = os.environ['AZURE_OPENAI_API_VERSION']

df = pd.read_csv(raw_data_path, delimiter=';')


def combine(x):
    res = ''
    to_concat = ['description', 'title', 'city', 'address']
    for item in to_concat:
        if x[item]:
            res += f'{item}: {x[item]}\n'
    return res


def create_index(df: pd.DataFrame):
    if os.path.exists(docs_filtered_path) and os.path.isdir(
        docs_filtered_path
    ):
        shutil.rmtree(docs_filtered_path)
    os.mkdir(docs_filtered_path)
    file_names = ['accomodations', 'events', 'landmarks', 'restaurants']

    for tag in file_names:
        df_filtered = df[df['tag'] == tag].copy(deep=True).fillna('')
        to_concat = ['description', 'title', 'city', 'address']
        df_filtered['index'] = df_filtered[to_concat].agg(combine, axis=1)
        df_filtered = df_filtered[['index']]
        df_filtered.to_csv(
            f'{docs_filtered_path}/{tag}.csv',
            index=False,
            index_label=False,
            sep=';',
        )

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=deployment,
        openai_api_version='2023-05-15',
    )

    if os.path.exists(index_path) and os.path.isdir(index_path):
        shutil.rmtree(index_path)
    os.mkdir(index_path)
    for tag in file_names:
        csv_loader = CSVLoader(
            file_path=f'./{docs_filtered_path}/{tag}.csv',
            csv_args={
                'delimiter': ';',
                'quotechar': '"',
                'fieldnames': ['data'],
            },
        )
        data = csv_loader.load()[1:]
        Chroma.from_documents(
            data,
            embedding=embeddings,
            persist_directory=f'./{index_path}/{tag}/chroma',
        )


def create_cities_csv(df: pd.DataFrame):
    pd.DataFrame(
        {'city': [(unidecode(city.lower())) for city in set(df['city'])]}
    ).to_csv(f'{index_path}/cities.csv', sep=';', index=False)

def create_cities_with_tags_csv(df: pd.DataFrame):
    data = [(unidecode(city.lower())) for city in set(df['city'] + '!!!' + df['tag'])]
    data = [x.split('!!!') for x in data]
    arg = {
        'city': [x[0] for x in data],
        'tag': [x[1] for x in data]
    }
    pd.DataFrame(
        arg
    ).to_csv(f'{index_path}/cities_with_tags.csv', sep=';', index=False)

create_index(df)
create_cities_csv(df)
create_cities_with_tags_csv(df)
shutil.make_archive(f'{index_path}', 'zip', index_path)
