import json
import logging
import os
from collections import defaultdict
from typing import Union, List, Dict


from gensim.models import KeyedVectors, Word2Vec
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim import utils
import numpy as np
from gensim.scripts.glove2word2vec import glove2word2vec
from gensim.test.utils import get_tmpfile, datapath
from numpy import float32 as real
from tqdm import tqdm
# import torch
# from transformers import TFAutoModel, AutoTokenizer, AdamW, LongformerModel, LongformerTokenizer, AutoModel

from doc2vec_structures import DocumentKeyedVectors
from text_summarisation import Summarizer
from topic_modelling import TopicModeller
from utils import Preprocesser, Corpus, ConfigLoader, DataHandler

config = ConfigLoader.get_config()


def robust_vec_loading(pretrained_emb_path: str = None, binary: bool = False):
    logging.info(f'Load pretrained embeddings from {pretrained_emb_path}')
    if pretrained_emb_path is None:
        return None
    try:
        model = KeyedVectors.load_word2vec_format(pretrained_emb_path, binary=binary)
    except ValueError:
        glove_file = datapath(pretrained_emb_path)
        tmp_file = get_tmpfile("test_word2vec.txt")
        _ = glove2word2vec(glove_file, tmp_file)
        model = KeyedVectors.load_word2vec_format(tmp_file)
    logging.info('load completed')
    return model


def write_aspect_frequency_analyzis(aspects: Dict[str, List[List[str]]], doc_ids: List[str], save_name: str):
    document_aspect_dict = defaultdict(dict)
    for aspect_name, aspect_documents in aspects.items():
        for doc_id, document in zip(doc_ids, aspect_documents):
            document_aspect_dict[doc_id].update({aspect_name: len(document)})

    with open(f'aspects/{save_name}.json', 'w', encoding="utf-8") as fp:
        json.dump(document_aspect_dict, fp, indent=1)
    return document_aspect_dict


class Vectorizer:
    workers = 1
    seed = 42
    window = 10
    min_count = 0
    epochs = 20
    dim = 300
    pretrained_emb_path = None  # config["embeddings"]["pretrained"]
    # "E:/embeddings/glove.6B.300d.txt" # "E:/embeddings/google300.txt"
    pretrained_emb = robust_vec_loading(pretrained_emb_path, binary=False)

    @staticmethod
    def build_vec_file_name(number_of_subparts: int, size: int, dataset: str, filter_mode: str,
                            vectorization_algorithm: str, fake_series: str) \
            -> str:
        sub_path = DataHandler.build_config_str(number_of_subparts, size, dataset, filter_mode,
                                                vectorization_algorithm, fake_series)
        return os.path.join(config["system_storage"]["models"], f'{sub_path}.model')

    @staticmethod
    def algorithm(input_str: str, corpus: Corpus, save_path: str = "models/", filter_mode: str = None,
                  return_vecs: bool = False):
        if input_str == "avg_wv2doc":
            return Vectorizer.avg_wv2doc(corpus, save_path, return_vecs=return_vecs)
        elif input_str == "avg_wv2doc_untrained":
            return Vectorizer.avg_wv2doc(corpus, save_path, return_vecs=return_vecs, without_training=True)
        elif input_str == "doc2vec":
            return Vectorizer.doc2vec(corpus, save_path, return_vecs=return_vecs)
        elif input_str == "doc2vec_untrained":
            return Vectorizer.doc2vec(corpus, save_path, return_vecs=return_vecs, without_training=True)
        # elif input_str == "longformer" or "longformer_untuned" or "untuned_longformer":
        #     return Vectorizer.longformer_untuned(corpus, save_path, return_vecs=return_vecs)
        # elif input_str == "longformer_tuned" or "tuned_longformer":
        #     return Vectorizer.longformer_tuned(corpus, save_path, return_vecs=return_vecs)
        elif input_str == "book2vec_simple" or input_str == "book2vec":
            return Vectorizer.book2vec_simple(corpus, save_path, return_vecs=return_vecs)
        elif input_str == "book2vec_wo_raw":
            return Vectorizer.book2vec_simple(corpus, save_path,
                                              disable_aspects=['raw'], return_vecs=return_vecs)
        elif input_str == "book2vec_wo_loc":
            return Vectorizer.book2vec_simple(corpus, save_path,
                                              disable_aspects=['loc'], return_vecs=return_vecs)
        elif input_str == "book2vec_wo_time":
            return Vectorizer.book2vec_simple(corpus, save_path,
                                              disable_aspects=['time'], return_vecs=return_vecs)
        elif input_str == "book2vec_wo_sty":
            return Vectorizer.book2vec_simple(corpus, save_path,
                                              disable_aspects=['sty'], return_vecs=return_vecs)
        elif input_str == "book2vec_wo_atm":
            return Vectorizer.book2vec_simple(corpus, save_path,
                                              disable_aspects=['atm'], return_vecs=return_vecs)
        elif input_str == "book2vec_simple_untrained" or input_str == "book2vec_untrained":
            return Vectorizer.book2vec_simple(corpus, save_path, return_vecs=return_vecs,
                                              without_training=True)
        elif input_str == "book2vec_adv":
            return Vectorizer.book2vec_adv(corpus, save_path, return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_raw":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['raw'], return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_loc":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['loc'], return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_time":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['time'], return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_sty":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['sty'], return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_atm":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['atm'], return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_plot":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['plot'], return_vecs=return_vecs)
        elif input_str == "book2vec_adv_wo_cont":
            return Vectorizer.book2vec_adv(corpus, save_path,
                                           disable_aspects=['cont'], return_vecs=return_vecs)
        elif input_str == "book2vec_w2v":
            return Vectorizer.book2vec_multi_algorithm_base(corpus, save_path,
                                                            disable_aspects=['cont'],
                                                            return_vecs=return_vecs,
                                                            algorithm="avg_w2v")
        elif input_str == "random_aspect2vec" or input_str == "random":
            return Vectorizer.random_aspect2vec(corpus, save_path, return_vecs=return_vecs,
                                                algorithm="doc2vec")
        else:
            raise UserWarning(f"fUnknown input string {input_str}!")

    @classmethod
    def word2vec_base(cls, preprocessed_sentences: List[List[str]], preprocessed_documents: List[str], doc_ids,
                      without_training: bool):
        if cls.pretrained_emb_path:
            model = cls.pretrained_emb

        else:
            # model = Word2Vec(preprocessed_sentences, size=cls.dim, window=cls.window, min_count=cls.min_count,
            #                  workers=cls.workers, iter=cls.epochs, seed=cls.seed)
            model = Word2Vec(size=cls.dim, window=cls.window, min_count=cls.min_count,
                             workers=cls.workers, seed=cls.seed)
            model.build_vocab(preprocessed_sentences)
            if not without_training:
                model.train(preprocessed_sentences, total_examples=model.corpus_count, epochs=cls.epochs)
        docs_dict = {}
        for doc_id, doc in zip(doc_ids, preprocessed_documents):
            vector = []
            if isinstance(doc, TaggedDocument):
                doc = doc.words
                # print(doc_id, doc)
            if len(doc) == 0:
                continue
            for token in doc:
                # print(token, model.wv.vocab[token])
                try:
                    vector.append(model.wv[token])
                except KeyError:
                    logging.error(f'KeyError Error for {doc_id} and {token}')
            # print(doc_id, doc, vector)
            try:
                vector = sum(np.array(vector)) / len(vector)
                docs_dict[doc_id] = vector
            except ZeroDivisionError:
                logging.error(f'ZeroDivision Error for {doc_id}')
                raise UserWarning(f"ZeroDevision Error for {doc_id}")

        words_dict = {word: model.wv[word] for word in model.wv.vocab}
        return model, words_dict, docs_dict

    @classmethod
    def word2vec_base_adv(cls, preprocessed_documents: List[str], doc_ids,
                          without_training: bool):
        if cls.pretrained_emb_path:
            model = cls.pretrained_emb

        else:
            # model = Word2Vec(preprocessed_sentences, size=cls.dim, window=cls.window, min_count=cls.min_count,
            #                  workers=cls.workers, iter=cls.epochs, seed=cls.seed)
            model = Word2Vec(size=cls.dim, window=cls.window, min_count=cls.min_count,
                             workers=cls.workers, seed=cls.seed)
            print(preprocessed_documents)
            model.build_vocab(preprocessed_documents)
            if not without_training:
                model.train(preprocessed_documents, total_examples=model.corpus_count, epochs=cls.epochs)
        docs_dict = {}
        for doc_id, doc in zip(doc_ids, preprocessed_documents):
            vector = []

            for token in doc:
                # print(token, model.wv.vocab[token])
                try:
                    vector.append(model.wv[token])
                except KeyError:
                    logging.error(f'KeyError Error for {doc_id} and {token}')
            # print(doc_id, doc, vector)
            try:
                vector = sum(np.array(vector)) / len(vector)
                docs_dict[doc_id] = vector
            except ZeroDivisionError:
                logging.error(f'ZeroDivision Error for {doc_id}')
                raise UserWarning(f"ZeroDevision Error for {doc_id}")

        words_dict = {word: model.wv[word] for word in model.wv.vocab}
        return model, words_dict, docs_dict

    @classmethod
    def doc2vec_base(cls, documents: List[str], without_training: bool):
        # model = Doc2Vec(documents, vector_size=100, window=10, min_count=2, workers=4, epochs=20)
        # model = Doc2Vec(documents, vector_size=cls.dim, window=cls.window, min_count=cls.min_count,
        #                 workers=cls.workers, epochs=cls.epochs, pretrained_emb=cls.pretrained_emb_path, seed=cls.seed)
        model = Doc2Vec(vector_size=cls.dim, min_count=cls.min_count, epochs=cls.epochs,
                        pretrained_emb=cls.pretrained_emb_path, seed=cls.seed, workers=cls.workers,
                        window=cls.window)
        model.build_vocab(documents)
        if not without_training:
            model.train(documents, total_examples=model.corpus_count, epochs=model.epochs)
        # print(model.docvecs.doctags)
        # for tag in model.docvecs.doctags:
        #     if not (tag.endswith('_time') or tag.endswith('_loc')):
        #         new_vec = model.docvecs[tag] + model.docvecs[f'{tag}_time'] + model.docvecs[f'{tag}_loc']
        #         print(tag)
        #         print(model.docvecs[tag])
        #         print(new_vec)
        #     # print(model.docvecs[tag])
        # aspect_string = ''.join(disable_aspects)
        # print(model.docvecs.doctags)
        words_dict, docs_dict = Vectorizer.model2dict(model)
        return model, words_dict, docs_dict

    @classmethod
    def avg_wv2doc(cls, corpus: Corpus, save_path: str = "models/", return_vecs: bool = True,
                   without_training: bool = False):
        # Preprocesser.preprocess(return_in_sentence_format=True)
        # print('sents', preprocessed_sentences)
        # print(preprocessed_documents)
        _, doc_ids = corpus.get_texts_and_doc_ids()
        preprocessed_sentences = corpus.get_flat_corpus_sentences()
        preprocessed_documents = corpus.get_flat_document_tokens()

        # for d in preprocessed_documents:
        #     print(d[:10])
        # print(preprocessed_documents)
        model, words_dict, docs_dict = cls.word2vec_base(preprocessed_sentences,
                                                         preprocessed_documents,
                                                         doc_ids,
                                                         without_training)

        Vectorizer.my_save_doc2vec_format(fname=save_path, doctag_vec=docs_dict, word_vec=words_dict,
                                          prefix='*dt_',
                                          fvocab=None, binary=False)
        if return_vecs:
            vecs = Vectorizer.my_load_doc2vec_format(fname=save_path, binary=False)
            return vecs
        else:
            return True

    @classmethod
    def doc2vec(cls, corpus: Corpus, save_path: str = "models/", return_vecs: bool = True,
                without_training: bool = False):
        # documents = [TaggedDocument(doc, [i])
        #              for i, doc in enumerate(Preprocesser.tokenize(corpus.get_texts_and_doc_ids()))]
        # documents = [TaggedDocument(Preprocesser.tokenize(document.text), [doc_id])
        #              for doc_id, document in corpus.documents.items()]
        _, doc_ids = corpus.get_texts_and_doc_ids()
        preprocessed_documents = corpus.get_flat_document_tokens()
        # print(preprocessed_documents)
        documents = [TaggedDocument(preprocessed_document_text, [doc_id])
                     for preprocessed_document_text, doc_id in zip(preprocessed_documents, doc_ids)]
        # print(documents[0])
        model = Doc2Vec(vector_size=cls.dim, min_count=cls.min_count, epochs=cls.epochs,
                        pretrained_emb=cls.pretrained_emb_path, seed=cls.seed, workers=cls.workers, window=cls.window)
        model.build_vocab(documents)
        if not without_training:
            model.train(documents, total_examples=model.corpus_count, epochs=model.epochs)

        model, words_dict, docs_dict = cls.doc2vec_base(documents, without_training)
        Vectorizer.my_save_doc2vec_format(fname=save_path, doctag_vec=docs_dict, word_vec=words_dict,
                                          prefix='*dt_',
                                          fvocab=None, binary=False)

        if return_vecs:
            vecs = Vectorizer.my_load_doc2vec_format(fname=save_path, binary=False)
            return vecs
        else:
            return True

    # @classmethod
    # def longformer_untuned(cls, corpus: Corpus, save_path: str = "models/", return_vecs: bool = True,
    #                        without_training: bool = False):
    #     _, doc_ids = corpus.get_texts_and_doc_ids()
    #
    #     model_name = "allenai/longformer-base-4096"  # "bert-base-uncased"
    #     model = TFAutoModel.from_pretrained(model_name)
    #     tokenizer = AutoTokenizer.from_pretrained(model_name)
    #     documents = corpus.get_flat_documents()
    #
    #     tokenized_docs = tokenizer(
    #         documents,
    #         padding=True,
    #         truncation=True,
    #         return_tensors="tf"
    #     )
    #
    #     predicted_embeddings = model(tokenized_docs)
    #     # print(tf_outputs)
    #     docs_dict = {}
    #     for doc_id, out in zip(doc_ids, predicted_embeddings[1]):
    #         docs_dict[doc_id] = out.numpy()
    #
    #     path = save_path
    #
    #     Vectorizer.my_save_doc2vec_format(fname=path, doctag_vec=docs_dict,
    #                                       prefix='*dt_',
    #                                       fvocab=None, binary=False)
    #
    #     if return_vecs:
    #         vecs = Vectorizer.my_load_doc2vec_format(fname=path, binary=False)
    #         return vecs
    #     else:
    #         return True
    # 
    # @classmethod
    # def longformer_tuned(cls, corpus: Corpus, save_path: str = "models/", return_vecs: bool = True,
    #                        without_training: bool = False):
    #     _, doc_ids = corpus.get_texts_and_doc_ids()
    #
    #     model_name = "allenai/longformer-base-4096"  # "bert-base-uncased"
    #     model = AutoModel.from_pretrained(model_name)
    #     tokenizer = AutoTokenizer.from_pretrained(model_name)
    #     documents = corpus.get_flat_documents()
    #     print(documents)
    #     tokenized_docs = tokenizer(
    #         documents,
    #         padding=True,
    #         truncation=True,
    #         return_tensors="pt"
    #     )
    #
    #     # model = LongformerModel.from_pretrained('allenai/longformer-base-4096', return_dict=True)
    #     # tokenizer = LongformerTokenizer.from_pretrained('allenai/longformer-base-4096')
    #     # tokenized = tokenizer(tokenized_docs, padding=True, truncation=True, return_tensors="pt")
    #     device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    #     model.to(device)
    #     model.train()
    #
    #     # train_dataset = TokenizedDataset(tokenized)
    #     # train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True)
    #     optim = AdamW(model.parameters(), lr=5e-5)
    #     tokenized_batch = tokenized_docs
    #     nr_epochs = 2
    #     epoch_bar = tqdm(range(nr_epochs), desc=f'Epoch {0} with loss UNKKOWN')
    #     outputs = None
    #     for epoch in epoch_bar:
    #         # for tokenized_batch in train_loader:
    #         optim.zero_grad()
    #         tokenized_b = tokenized_batch.to(device)
    #         # input_ids = tokenized['input_ids'].to(device)
    #         # attention_mask = tokenized['attention_mask'].to(device)
    #         # labels = tokenized['input_ids'].to(device)
    #         # outputs = model(input_ids, labels=input_ids, attention_mask=attention_mask)
    #         # loss = outputs.pooler_output
    #         outputs = model(**tokenized_b)
    #         loss = outputs[0]
    #         epoch_bar.set_description(desc=f'Epoch {epoch} with loss {loss.sum():.2f}')
    #         epoch_bar.update()
    #         loss.sum().backward()
    #         optim.step()
    #
    #     docs_dict = {}
    #     for doc_id, out in zip(doc_ids, outputs[1]):
    #         docs_dict[doc_id] = out.detach().numpy()
    #
    #     path = save_path
    #
    #     Vectorizer.my_save_doc2vec_format(fname=path, doctag_vec=docs_dict,
    #                                       prefix='*dt_',
    #                                       fvocab=None, binary=False)
    #
    #     if return_vecs:
    #         vecs = Vectorizer.my_load_doc2vec_format(fname=path, binary=False)
    #         return vecs
    #     else:
    #         return True

    @classmethod
    def book2vec_simple(cls, corpus: Corpus, save_path: str = "models/",
                        disable_aspects: List[str] = None, return_vecs: bool = True, without_training: bool = False):
        lemma = False
        lower = False

        if disable_aspects is None:
            disable_aspects = []
        # documents = [TaggedDocument(doc, [i])
        #              for i, doc in enumerate(Preprocesser.tokenize(corpus.get_texts_and_doc_ids()))]
        # documents = [TaggedDocument(Preprocesser.tokenize(document.text), [doc_id])
        #              for doc_id, document in corpus.documents.items()]
        lan_model = corpus.give_spacy_lan_model()
        # print('>', preprocessed_documents)
        _, doc_ids = corpus.get_texts_and_doc_ids()
        if corpus.document_entities is None:
            raise UserWarning("No Entities set!")
        document_entities = corpus.get_document_entities_representation()
        # reverted_entities = Utils.revert_dictionaries(document_entities)
        # print('>', reverted_entities)
        times, locations = Vectorizer.resolve_entities(document_entities)
        # print(len(times), times)

        aspects = {}

        if "time" not in disable_aspects:
            aspects['time'] = Preprocesser.structure_string_texts(times, lan_model, lemma=lemma, lower=lower)

        if "loc" not in disable_aspects:
            aspects['loc'] = Preprocesser.structure_string_texts(locations, lan_model, lemma=lemma, lower=lower)

        # preprocessed_times, _, _ = Preprocesser.preprocess(times, lemmatize=False, lower=False,
        #                                                    pos_filter=None, remove_stopwords=False,
        #                                                    remove_punctuation=False,
        #                                                    lan_model=lan_model, ner=False)
        #
        # preprocessed_locations, _, _ = Preprocesser.preprocess(locations, lemmatize=False, lower=False,
        #                                                        pos_filter=None, remove_stopwords=False,
        #                                                        remove_punctuation=False,
        #                                                        lan_model=lan_model, ner=False)

        # print(preprocessed_times)

        if "raw" not in disable_aspects:
            aspects['raw'] = corpus.get_flat_document_tokens(lemma=lemma, lower=lower)

        if "atm" not in disable_aspects:
            aspects['atm'] = corpus.get_flat_and_filtered_document_tokens(lemma=lemma,
                                                                          lower=lower,
                                                                          pos=["ADJ", "ADV"])
        if "sty" not in disable_aspects:
            aspects['sty'] = corpus.get_flat_and_filtered_document_tokens(lemma=lemma,
                                                                          lower=lower,
                                                                          focus_stopwords=True)
        # if "cont" not in disable_aspects:
        #     _, topic_list = TopicModeller.train_lda(corpus)
        #     aspects["cont"] = topic_list
        #
        # if "plot" not in disable_aspects:
        #     aspects["plot"] = Summarizer.get_corpus_summary_sentence_list(corpus,
        #                                                                   lemma=lemma,
        #                                                                   lower=lower)
        # print(aspects.keys(), disable_aspects)
        # for key, values in aspects.items():
        #     for doc_list, doc_id in zip(values, doc_ids):
        #         print(key, doc_id, doc_list[:10])
        assert set(aspects.keys()).union(disable_aspects) == {'time', 'loc', 'raw', 'atm', 'sty'}
        aspect_path = os.path.basename(save_path)
        write_aspect_frequency_analyzis(aspects=aspects, doc_ids=doc_ids, save_name=aspect_path)

        documents = []
        for aspect_name, aspect_documents in aspects.items():
            documents.extend([TaggedDocument(preprocessed_document_text, [f'{doc_id}_{aspect_name}'])
                              for preprocessed_document_text, doc_id in zip(aspect_documents, doc_ids)])

        logging.info("Start training")

        model, words_dict, docs_dict = cls.doc2vec_base(documents, without_training)
        # print(docs_dict.keys())
        docs_dict = Vectorizer.combine_vectors_by_sum(docs_dict)
        # print(path)
        Vectorizer.my_save_doc2vec_format(fname=save_path, doctag_vec=docs_dict, word_vec=words_dict,
                                          prefix='*dt_',
                                          fvocab=None, binary=False)
        if return_vecs:
            vecs = Vectorizer.my_load_doc2vec_format(fname=save_path, binary=False)
            return vecs
        else:
            return True

    @classmethod
    def book2vec_adv(cls, corpus: Corpus, save_path: str = "models/",
                     disable_aspects: List[str] = None, return_vecs: bool = True, without_training: bool = False):
        lemma = False
        lower = False

        if disable_aspects is None:
            disable_aspects = []
        # documents = [TaggedDocument(doc, [i])
        #              for i, doc in enumerate(Preprocesser.tokenize(corpus.get_texts_and_doc_ids()))]
        # documents = [TaggedDocument(Preprocesser.tokenize(document.text), [doc_id])
        #              for doc_id, document in corpus.documents.items()]
        lan_model = corpus.give_spacy_lan_model()
        # print('>', preprocessed_documents)
        _, doc_ids = corpus.get_texts_and_doc_ids()
        if corpus.document_entities is None:
            raise UserWarning("No Entities set!")
        document_entities = corpus.get_document_entities_representation()
        # reverted_entities = Utils.revert_dictionaries(document_entities)
        # print('>', reverted_entities)
        times, locations = Vectorizer.resolve_entities(document_entities)
        # print(len(times), times)

        aspects = {}

        if "time" not in disable_aspects:
            aspects['time'] = Preprocesser.structure_string_texts(times, lan_model, lemma=lemma, lower=lower)

        if "loc" not in disable_aspects:
            aspects['loc'] = Preprocesser.structure_string_texts(locations, lan_model, lemma=lemma, lower=lower)

        # preprocessed_times, _, _ = Preprocesser.preprocess(times, lemmatize=False, lower=False,
        #                                                    pos_filter=None, remove_stopwords=False,
        #                                                    remove_punctuation=False,
        #                                                    lan_model=lan_model, ner=False)
        #
        # preprocessed_locations, _, _ = Preprocesser.preprocess(locations, lemmatize=False, lower=False,
        #                                                        pos_filter=None, remove_stopwords=False,
        #                                                        remove_punctuation=False,
        #                                                        lan_model=lan_model, ner=False)

        # print(preprocessed_times)

        if "raw" not in disable_aspects:
            aspects['raw'] = corpus.get_flat_document_tokens(lemma=lemma, lower=lower)

        if "atm" not in disable_aspects:
            aspects['atm'] = corpus.get_flat_and_filtered_document_tokens(lemma=lemma,
                                                                          lower=lower,
                                                                          pos=["ADJ", "ADV"])
        if "sty" not in disable_aspects:
            aspects['sty'] = corpus.get_flat_and_filtered_document_tokens(lemma=lemma,
                                                                          lower=lower,
                                                                          focus_stopwords=True)
        if "cont" not in disable_aspects:
            _, topic_list = TopicModeller.train_lda(corpus)
            aspects["cont"] = topic_list

        if "plot" not in disable_aspects:
            aspects["plot"] = Summarizer.get_corpus_summary_sentence_list(corpus,
                                                                          lemma=lemma,
                                                                          lower=lower)
        # print(aspects.keys(), disable_aspects)
        assert set(aspects.keys()).union(disable_aspects) == {'time', 'loc', 'raw', 'atm', 'sty', 'cont', 'plot'}
        aspect_path = os.path.basename(save_path)
        write_aspect_frequency_analyzis(aspects=aspects, doc_ids=doc_ids, save_name=aspect_path)

        documents = []
        for aspect_name, aspect_documents in aspects.items():
            documents.extend([TaggedDocument(preprocessed_document_text, [f'{doc_id}_{aspect_name}'])
                              for preprocessed_document_text, doc_id in zip(aspect_documents, doc_ids)])

        logging.info("Start training")
        model, words_dict, docs_dict = cls.doc2vec_base(documents, without_training)
        docs_dict = Vectorizer.combine_vectors_by_sum(docs_dict)
        # print(path)
        Vectorizer.my_save_doc2vec_format(fname=save_path, doctag_vec=docs_dict, word_vec=words_dict,
                                          prefix='*dt_',
                                          fvocab=None, binary=False)
        if return_vecs:
            vecs = Vectorizer.my_load_doc2vec_format(fname=save_path, binary=False)
            return vecs
        else:
            return True

    @staticmethod
    def build_simple_sentence_aspects(aspect: List[List[str]], corpus: Corpus):
        # print(aspect)
        sentence_aspect = [[[token.representation() for token in sentence.tokens
                             if token.representation() in aspect[i]]
                            for sentence in document.sentences]
                           for i, document in enumerate(corpus.documents.values())]
        # print(sentence_aspect)
        return sentence_aspect

    @classmethod
    def book2vec_multi_algorithm_base(cls, corpus: Corpus, save_path: str = "models/",
                                      disable_aspects: List[str] = None, return_vecs: bool = True, algorithm="doc2vec",
                                      without_training: bool = False):
        lemma = False
        lower = False

        if disable_aspects is None:
            disable_aspects = []
        # documents = [TaggedDocument(doc, [i])
        #              for i, doc in enumerate(Preprocesser.tokenize(corpus.get_texts_and_doc_ids()))]
        # documents = [TaggedDocument(Preprocesser.tokenize(document.text), [doc_id])
        #              for doc_id, document in corpus.documents.items()]
        lan_model = corpus.give_spacy_lan_model()
        # print('>', preprocessed_documents)
        _, doc_ids = corpus.get_texts_and_doc_ids()
        if corpus.document_entities is None:
            raise UserWarning("No Entities set!")
        document_entities = corpus.get_document_entities_representation()
        # reverted_entities = Utils.revert_dictionaries(document_entities)
        # print('>', reverted_entities)
        times, locations = Vectorizer.resolve_entities(document_entities)
        # print(len(times), times)

        aspects = {}
        # sentence_aspects = {}

        if "time" not in disable_aspects:
            aspects['time'] = Preprocesser.structure_string_texts(times, lan_model, lemma=lemma, lower=lower)

        if "loc" not in disable_aspects:
            aspects['loc'] = Preprocesser.structure_string_texts(locations, lan_model, lemma=lemma, lower=lower)

        if "raw" not in disable_aspects:
            aspects['raw'] = corpus.get_flat_document_tokens(lemma=lemma, lower=lower)

        if "atm" not in disable_aspects:
            aspects['atm'] = corpus.get_flat_and_filtered_document_tokens(lemma=lemma,
                                                                          lower=lower,
                                                                          pos=["ADJ", "ADV"])

        if "sty" not in disable_aspects:
            aspects['sty'] = corpus.get_flat_and_filtered_document_tokens(lemma=lemma,
                                                                          lower=lower,
                                                                          focus_stopwords=True)

        if "cont" not in disable_aspects:
            _, topic_list = TopicModeller.train_lda(corpus)
            aspects["cont"] = topic_list

        if "plot" not in disable_aspects:
            aspects["plot"] = Summarizer.get_corpus_summary_sentence_list(corpus,
                                                                          lemma=lemma,
                                                                          lower=lower)

        # print(aspects.keys(), disable_aspects)
        assert set(aspects.keys()).union(disable_aspects) == {'time', 'loc', 'raw', 'atm', 'sty', 'cont', 'plot'}
        aspect_path = os.path.basename(save_path)
        write_aspect_frequency_analyzis(aspects=aspects, doc_ids=doc_ids, save_name=aspect_path)

        documents = []
        for aspect_name, aspect_documents in aspects.items():
            documents.extend([TaggedDocument(preprocessed_document_text, [f'{doc_id}_{aspect_name}'])
                              for preprocessed_document_text, doc_id in zip(aspect_documents, doc_ids)])

        logging.info("Start training")
        if algorithm.lower() == "doc2vec" or algorithm.lower() == "d2v":
            model, words_dict, docs_dict = cls.doc2vec_base(documents, without_training)
        elif algorithm.lower() == "avg_w2v" or algorithm.lower() == "w2v" or algorithm.lower() == "word2vec":
            preprocessed_sentences = corpus.get_flat_corpus_sentences()
            aspect_doc_ids = [d.tags[0] for d in documents]
            model, words_dict, docs_dict = cls.word2vec_base(preprocessed_sentences, documents,
                                                             aspect_doc_ids, without_training)
        else:
            raise UserWarning(f"Not supported vectorization algorithm '{algorithm}'!")

        docs_dict = Vectorizer.combine_vectors_by_sum(docs_dict)
        Vectorizer.my_save_doc2vec_format(fname=save_path, doctag_vec=docs_dict, word_vec=words_dict,
                                          prefix='*dt_',
                                          fvocab=None, binary=False)
        if return_vecs:
            vecs = Vectorizer.my_load_doc2vec_format(fname=save_path, binary=False)
            return vecs
        else:
            return True

    @classmethod
    def random_aspect2vec(cls, corpus: Corpus, save_path: str = "models/",
                          return_vecs: bool = True, algorithm="doc2vec",
                          without_training: bool = False):
        def nr_to_roman(nr: int):
            if nr == 0:
                return 'I'
            elif nr == 1:
                return 'II'
            elif nr == 2:
                return 'III'
            elif nr == 3:
                return 'IV'
            elif nr == 4:
                return 'V'
            elif nr == 5:
                return 'VI'
            elif nr == 6:
                return 'VII'
            elif nr == 7:
                return 'VIII'
            elif nr == 8:
                return 'IX'
            elif nr == 9:
                return 'X'
            elif nr == 10:
                return 'XI'

        lemma = False
        lower = False
        _, doc_ids = corpus.get_texts_and_doc_ids()
        if corpus.document_entities is None:
            raise UserWarning("No Entities set!")

        aspects = {}
        prob_to_keep = 0.2
        nr_aspects = 5
        aspects['raw'] = corpus.get_flat_document_tokens(lemma=lemma, lower=lower)

        for aspect_nr in range(0, nr_aspects):
            aspects[f'aspect{nr_to_roman(aspect_nr)}'] = corpus.get_flat_and_random_document_tokens(prop_to_keep=prob_to_keep,
                                                                                       seed=aspect_nr,
                                                                                       lemma=lemma,
                                                                                       lower=lower)
        documents = []
        for aspect_name, aspect_documents in aspects.items():
            documents.extend([TaggedDocument(preprocessed_document_text, [f'{doc_id}_{aspect_name}'])
                              for preprocessed_document_text, doc_id in zip(aspect_documents, doc_ids)])

        logging.info("Start training")
        if algorithm.lower() == "doc2vec" or algorithm.lower() == "d2v":
            model, words_dict, docs_dict = cls.doc2vec_base(documents, without_training)
        elif algorithm.lower() == "avg_w2v" or algorithm.lower() == "w2v" or algorithm.lower() == "word2vec":
            preprocessed_sentences = corpus.get_flat_corpus_sentences()
            aspect_doc_ids = [d.tags[0] for d in documents]
            model, words_dict, docs_dict = cls.word2vec_base(preprocessed_sentences, documents,
                                                             aspect_doc_ids, without_training)
        else:
            raise UserWarning(f"Not supported vectorization algorithm '{algorithm}'!")
        docs_dict = Vectorizer.combine_vectors_by_sum(docs_dict)
        Vectorizer.my_save_doc2vec_format(fname=save_path, doctag_vec=docs_dict, word_vec=words_dict,
                                          prefix='*dt_',
                                          fvocab=None, binary=False)
        if return_vecs:
            vecs = Vectorizer.my_load_doc2vec_format(fname=save_path, binary=False)
            return vecs
        else:
            return True

    @staticmethod
    def combine_vectors_by_sum(document_dictionary: Dict[str, np.array]):
        summed_vecs = {}

        base_ending_candidates = set([f"_{tag.split('_')[-1]}" for tag in document_dictionary.keys()])

        candidate_counter_dict = defaultdict(int)
        plain_doc_ids = set()
        for base_ending_candidate in base_ending_candidates:
            for doc_id in document_dictionary.keys():
                splitted_id = doc_id.split('_')
                prefix = '_'.join(splitted_id[:-1])
                suffix = f"_{splitted_id[-1]}"
                plain_doc_ids.add(prefix)

                if base_ending_candidate == suffix:
                    candidate_counter_dict[base_ending_candidate] += 1

        final_candidates = [candidate for candidate, count in candidate_counter_dict.items()
                                  if count == len(plain_doc_ids)]

        if len(final_candidates) == 0:
            raise UserWarning("No aspect found for all documents")
        base_ending = final_candidates[0]

        id_groups = set([tag.split('_')[-1] for tag in document_dictionary.keys() if not tag.endswith(base_ending)])
        # print(base_ending, id_groups, document_dictionary.keys())

        for tag in document_dictionary.keys():
            if tag.endswith(base_ending):
                new_vec = document_dictionary[tag]
                base_tag = tag.replace(base_ending, '')
                for group in id_groups:
                    try:
                        new_vec += document_dictionary[f'{base_tag}_{group}']
                    except KeyError:
                        pass
                summed_vecs[f'{base_tag}'] = new_vec
            # print(model.docvecs[tag])
        summed_vecs.update(document_dictionary)
        return summed_vecs


    @staticmethod
    def resolve_entities(entities_of_documents):
        time_sets = []
        location_sets = []
        for doc_id, entities_of_document_dict in entities_of_documents.items():
            # Time
            # entities_of_document = entities_of_document_dict
            entities_of_document = defaultdict(str, entities_of_document_dict)
            # ToDo: set or list?
            time_set = list(entities_of_document['DATE'])
            time_set.extend(entities_of_document['TIME'])
            # TODO: special handling required
            time_set.extend(entities_of_document['EVENT'])
            time_sets.append(' '.join(time_set))
            # Location
            location_set = list(entities_of_document['FAC'])
            location_set.extend(entities_of_document['GPE'])
            location_set.extend(entities_of_document['LOC'])
            location_sets.append(' '.join(location_set))

            # # Use Maybe
            # # Subjects and Objects
            # entities_of_document['PERSON']
            # entities_of_document['NORP']
            # entities_of_document['ORG']
            # entities_of_document['PRODUCT']
            # entities_of_document['WORK_OF_ART']
            #
            # # Unused
            # ## Numbers
            # entities_of_document['PERCENT']
            # entities_of_document['MONEY']
            # entities_of_document['QUANTITY']
            # entities_of_document['ORDINAL']
            # entities_of_document['CARDINAL']
            # ## Language
            # entities_of_document['LAW']
            # entities_of_document['LANGUAGE']

        return time_sets, location_sets

    @staticmethod
    def model2dict(model: Doc2Vec):
        words_dict = {word: model.wv[word] for word in model.wv.vocab}
        doc_dict = {doc_id: model.docvecs[doc_id] for doc_id in model.docvecs.doctags}
        # print(model.__index_to_doctag(i, self.offset2doctag, self.max_rawint))
        # print('>>', model.docvecs.vectors_docs)
        # print('>>', model.docvecs.max_rawint)
        return words_dict, doc_dict

    @staticmethod
    def my_save_word2vec_format(fname: str, vocab: Dict[str, np.ndarray], vectors: np.ndarray, binary: bool = True,
                                total_vec: int = 2):
        """Store the input-hidden weight matrix in the same format used by the original
        C word2vec-tool, for compatibility.
        Parameters
        ----------
        fname : str
            The file path used to save the vectors in.
        vocab : dict
            The vocabulary of words.
        vectors : numpy.array
            The vectors to be stored.
        binary : bool, optional
            If True, the data wil be saved in binary word2vec format, else it will be saved in plain text.
        total_vec : int, optional
            Explicitly specify total number of vectors
            (in case word vectors are appended with document vectors afterwards).
        """
        if not (vocab or vectors):
            raise RuntimeError("no input")
        if total_vec is None:
            total_vec = len(vocab)
        vector_size = vectors.shape[1]
        assert (len(vocab), vector_size) == vectors.shape

        with utils.open(fname, 'wb') as fout:
            fout.write(utils.to_utf8("%s %s\n" % (total_vec, vector_size)))
            # store in sorted order: most frequent words at the top
            for word, row in vocab.items():
                if binary:
                    row = row.astype(real)
                    fout.write(utils.to_utf8(word) + b" " + row.tostring())
                else:
                    fout.write(utils.to_utf8("%s %s\n" % (word, ' '.join(repr(val) for val in row))))

    @staticmethod
    def my_save_docvec_word2vec_format(fname, docvecs: Dict[str, np.ndarray], prefix='*dt_', fvocab=None,
                                       total_vec=None, binary=False, write_first_line=True):
        """Store the input-hidden weight matrix in the same format used by the original
        C word2vec-tool, for compatibility.

        Parameters
        ----------
        fname : str
            The file path used to save the vectors in.
        docvecs : Dict[str, np.array]: actual document vectors
        prefix : str, optional
            Uniquely identifies doctags from word vocab, and avoids collision
            in case of repeated string in doctag and word vocab.
        fvocab : str, optional
            UNUSED.
        total_vec : int, optional
            Explicitly specify total no. of vectors
            (in case word vectors are appended with document vectors afterwards)
        binary : bool, optional
            If True, the data will be saved in binary word2vec format, else it will be saved in plain text.
        write_first_line : bool, optional
            Whether to print the first line in the file. Useful when saving doc-vectors after word-vectors.


        """

        def _index_to_doctag(i_index, offset, max_rawint_value):
            """Get string key for given `i_index`, if available. Otherwise return raw int doctag (same int)."""
            candidate_offset = i_index - max_rawint_value - 1
            if 0 <= candidate_offset < len(offset):
                return offset[candidate_offset]
            else:
                return i_index

        len_docvecs = len(docvecs)
        offset2doctag = list(docvecs.keys())
        vectors_docs = np.array(list(docvecs.values()))

        max_rawint = -1

        total_vec = total_vec or len_docvecs
        with utils.open(fname, 'ab') as fout:
            if write_first_line:
                fout.write(utils.to_utf8("%s %s\n" % (total_vec, vectors_docs.shape[1])))
            # store as in input order
            for i in range(len_docvecs):
                doctag = u"%s%s" % (prefix, _index_to_doctag(i, offset2doctag, max_rawint))
                row = vectors_docs[i]
                if binary:
                    fout.write(utils.to_utf8(doctag) + b" " + row.tostring())
                else:
                    fout.write(utils.to_utf8("%s %s\n" % (doctag, ' '.join("%f" % val for val in row))))

    @staticmethod
    def my_save_doc2vec_format(fname, doctag_vec: Dict[str, np.ndarray] = None, word_vec: Dict[str, np.ndarray] = None,
                               prefix='*dt_', fvocab=None, binary=False):
        """Store the input-hidden weight matrix in the same format used by the original C word2vec-tool.

        Parameters
        ----------
        fname : str
            The file path used to save the vectors in.
        doctag_vec : bool, optional
            Indicates whether to store document vectors.
        word_vec : bool, optional
            Indicates whether to store word vectors.
        prefix : str, optional
            Uniquely identifies doctags from word vocab, and avoids collision in case of repeated string in doctag
            and word vocab.
        fvocab : str, optional
            Optional file path used to save the vocabulary.
        binary : bool, optional
            If True, the data will be saved in binary word2vec format, otherwise - will be saved in plain text.

        """
        if os.path.isfile(fname):
            os.remove(fname)
        docvecs = doctag_vec
        wv_vocab = word_vec  # self.wv.vocab

        write_first_line = False
        # save word vectors
        if word_vec:
            if not doctag_vec:
                total_vec = len(wv_vocab)
            else:
                total_vec = len(wv_vocab) + len(docvecs)
            wv_vectors = np.array(list(word_vec.values()))  # self.wv.vectors
            # self.wv.save_word2vec_format(fname, fvocab, binary, total_vec)
            Vectorizer.my_save_word2vec_format(fname, wv_vocab, wv_vectors, binary, total_vec)
        # save document vectors
        if doctag_vec:
            if not word_vec:
                total_vec = len(docvecs)
                write_first_line = True
            else:
                total_vec = len(wv_vocab) + len(docvecs)
            # self.docvecs.save_word2vec_format(
            #     fname, prefix=prefix, fvocab=fvocab, total_vec=total_vec,
            #     binary=binary, write_first_line=write_first_line)
            Vectorizer.my_save_docvec_word2vec_format(fname, doctag_vec, prefix, fvocab, total_vec, binary,
                                                      write_first_line)

    @staticmethod
    def my_load_doc2vec_format(fname: str, binary: bool = False):
        return DocumentKeyedVectors(KeyedVectors.load_word2vec_format(fname=fname, binary=binary))

    # @staticmethod
    # def show_results(model: Union[Doc2Vec, DocumentKeyedVectors], corpus: Corpus):
    #
    #     # print(model.docvecs[0])
    #     # print(model.docvecs.doctags)
    #     # print(model.docvecs.distance())
    #
    #     # print(model.wv.most_similar('God'))
    #     # print(model.wv.most_similar([model['God']]))
    #     # print('------')
    #     # print(model.wv.most_similar([model.docvecs['bs_0']]))
    #     # print('--')
    #     Vectorizer.most_similar_words_to_documents(model, positives=['bs_0'])
    #
    #     # finish = 100
    #     # c = 0
    #     # for doc_id, document in corpus.documents.items():
    #     #     print(doc_id, corpus.id2desc(doc_id), model.wv.most_similar([model.docvecs[doc_id]]))
    #     #     if c > finish:
    #     #         break
    #     #     c += 1
    #     # print('------')
    #     # print(model.wv.most_similar(positive=[model.docvecs['bs_0'], model.docvecs['bs_1']],
    #     #                             negative=[model.docvecs['bs_2']]))
    #     # print('--')
    #     Vectorizer.most_similar_words_to_documents(model, positives=['bs_0', 'bs_1'], negatives=['bs_2'])
    #     # print('------')
    #     # for result in model.docvecs.most_similar(positive=[model.docvecs['bs_0'], model.docvecs['bs_1']],
    #     #                                          negative=[model.docvecs['bs_2']]):
    #     #     index, sim = result
    #     #     print(index, corpus.id2desc(index), sim)
    #     # print('--')
    #     Vectorizer.most_similar_documents_to_documents(model, corpus, positives=['bs_0', 'bs_1'], negatives=['bs_2'])
    #
    #     # print('------')
    #     # for result in model.docvecs.most_similar([model['God']]):
    #     #     index, sim = result
    #     #     print(index, corpus.id2desc(index), sim)
    #     # print('--')
    #     Vectorizer.most_similar_documents_to_words(model, corpus, positives=['God'])
    #
    #     # print('------')
    #     # for result in model.docvecs.most_similar(positive=[model['woman'], model['king']], negative=[model['man']]):
    #     #     index, sim = result
    #     #     print(index, corpus.id2desc(index), sim)
    #     # print('--')
    #     Vectorizer.most_similar_documents_to_words(model, corpus, positives=['woman', 'god'], negatives=['man'])
    #     # Vectorizer.most_similar_documents_to_words(model, corpus, positives=['queen'])

    @staticmethod
    def get_topn_of_same_type(model: Union[Doc2Vec, DocumentKeyedVectors],
                              positive_tags: List[str],
                              positive_list: List[str], negative_list: List[str],
                              topn: int,
                              feature_to_use: str = None,
                              origin_topn: int = None):

        def extract_feature(tag_list):
            tag = tag_list[0]
            if tag[-1].isdigit():
                return 'NF'
            splitt = tag.split('_')
            # print(splitt[-1])
            return f"_{splitt[-1]}"

        high_topn = topn * 10
        # print(feature_to_use)
        if feature_to_use:
            feature = feature_to_use
        else:
            feature = extract_feature(positive_tags)
        results = model.docvecs.most_similar(positive=positive_list, negative=negative_list, topn=high_topn)

        if feature == 'NF':
            results = [result for result in results if result[0][-1].isdigit()]
        else:
            results = [result for result in results if result[0].endswith(feature)]

        # print(results)
        if origin_topn is None:
            origin_topn = topn

        if len(results) >= origin_topn:
            return results[:origin_topn]
        else:
            return Vectorizer.get_topn_of_same_type(model, positive_tags, positive_list, negative_list, high_topn,
                                                    feature_to_use, origin_topn)[:topn]

    # @staticmethod
    # def most_similar_words_to_documents(model: Union[Doc2Vec, DocumentKeyedVectors],
    #                                     positives: List[str],
    #                                     negatives: List[str] = None,
    #                                     topn: int = 10):
    #     if negatives is None:
    #         negatives = []
    #     positive_list = []
    #     for word in positives:
    #         positive_list.append(model.docvecs[word])
    #
    #     negative_list = []
    #     for word in negatives:
    #         negative_list.append(model.docvecs[word])
    #     results = model.wv.most_similar(positive=positive_list, negative=negative_list, topn=topn)
    #     for result in results:
    #         word, sim = result
    #         print(word, sim)
    #
    # @staticmethod
    # def most_similar_documents_to_words(model: Union[Doc2Vec, DocumentKeyedVectors],
    #                                     corpus: Corpus, positives: List[str],
    #                                     negatives=None,
    #                                     topn: int = 10,
    #                                     restrict_to_same: bool = True,
    #                                     feature_to_use: str = None):
    #     if feature_to_use is None:
    #         feature_to_use = "NF"
    #     if negatives is None:
    #         negatives = []
    #     positive_list = []
    #     for word in positives:
    #         positive_list.append(model.wv[word])
    #
    #     negative_list = []
    #     for word in negatives:
    #         negative_list.append(model.wv[word])
    #
    #     if restrict_to_same:
    #         results = Vectorizer.get_topn_of_same_type(model, positives, positive_list, negative_list, topn,
    #                                                    feature_to_use=feature_to_use)
    #     else:
    #         results = model.docvecs.most_similar(positive=positive_list, negative=negative_list, topn=topn)
    #     for result in results:
    #         index, sim = result
    #         print(index, corpus.id2desc(index), sim)
    #
    # @staticmethod
    # def most_similar_documents_to_documents(model: Union[Doc2Vec, DocumentKeyedVectors],
    #                                         corpus: Corpus, positives: Union[List[str], str],
    #                                         negatives: Union[List[str], str] = None,
    #                                         topn: int = 10,
    #                                         restrict_to_same: bool = True,
    #                                         feature_to_use: str = None):
    #     positive_list = []
    #     if isinstance(positives, str):
    #         positives = [positives]
    #
    #     for doc_id in positives:
    #         positive_list.append(model.docvecs[doc_id])
    #
    #     if negatives is None:
    #         negatives = []
    #     elif isinstance(negatives, str):
    #         negatives = [negatives]
    #     else:
    #         pass
    #
    #     negative_list = []
    #     for doc_id in negatives:
    #         negative_list.append(model.docvecs[doc_id])
    #
    #     if restrict_to_same:
    #         results = Vectorizer.get_topn_of_same_type(model, positives, positive_list, negative_list, topn,
    #                                                    feature_to_use)
    #     else:
    #         results = model.docvecs.most_similar(positive=positive_list, negative=negative_list, topn=topn)
    #     for result in results:
    #         index, sim = result
    #         print(index, corpus.id2desc(index), sim)

    @staticmethod
    def most_similar_documents(model: Union[Doc2Vec, DocumentKeyedVectors],
                               corpus: Corpus, positives: Union[List[str], str],
                               negatives: Union[List[str], str] = None,
                               topn: int = 10,
                               restrict_to_same: bool = True,
                               feature_to_use: str = None,
                               print_results: bool = True):

        def get_list(input_list, input_model):
            out_list = []
            if input_list is None:
                input_list = []
            elif isinstance(input_list, str):
                input_list = [input_list]
            else:
                pass
            for document_id in input_list:
                try:
                    out_list.append(input_model.docvecs[document_id])
                except KeyError:
                    try:
                        out_list.append(input_model.wv[document_id])
                    except KeyError:
                        if document_id.count('_') > 1:
                            nr = '_'.join(document_id.split('_')[1:])
                        else:
                            nr = document_id
                        prefix = list(input_model.docvecs.doctags.keys())[0].split('_')[0]
                        new_id = f'{prefix}_{nr}'
                        # print(new_id)
                        out_list.append(input_model.docvecs[new_id])
            return out_list

        positive_list = get_list(positives, model)
        negative_list = get_list(negatives, model)

        if restrict_to_same:
            results = Vectorizer.get_topn_of_same_type(model, positives, positive_list, negative_list, topn,
                                                       feature_to_use)
        else:
            results = model.docvecs.most_similar(positive=positive_list, negative=negative_list, topn=topn)

        if print_results:
            for result in results:
                index, sim = result
                print(index, corpus.id2desc(index), sim)
        return results

    @staticmethod
    def most_similar_words(model: Union[Doc2Vec, DocumentKeyedVectors],
                           positives: List[str],
                           negatives: List[str] = None,
                           topn: int = 10):
        if negatives is None:
            negatives = []
        positive_list = []
        for word in positives:
            try:
                positive_list.append(model.docvecs[word])
            except KeyError:
                positive_list.append(model.wv[word])

        negative_list = []
        for word in negatives:
            try:
                negative_list.append(model.docvecs[word])
            except KeyError:
                negative_list.append(model.wv[word])
        results = model.wv.most_similar(positive=positive_list, negative=negative_list, topn=topn)
        for result in results:
            word, sim = result
            print(word, sim)
