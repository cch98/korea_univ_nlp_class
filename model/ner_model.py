import numpy as np
import os
import re
import tensorflow as tf


from .data_utils import minibatches, pad_sequences, get_chunks
from .general_utils import Progbar
from .base_model import BaseModel


class NERModel(BaseModel):
    """Specialized class of Model for NER"""

    def __init__(self, config):
        super(NERModel, self).__init__(config) # inheritance BaseModel
        self.idx_to_tag = {idx: tag for tag, idx in
                           self.config.vocab_tags.items()}
        # {0: 'I-PER', 1: 'I-LOC', 2: 'B-MISC', 3: 'B-PER', 4: 'I-ORG', 5: 'B-ORG', 6: 'O', 7: 'I-MISC', 8: 'B-LOC'}


    def add_placeholders(self):
        """Define placeholders = entries to computational graph"""
        
        # shape = (batch size, max length of sentence in batch)
        self.word_ids = tf.placeholder(tf.int32, shape=[None, None],
                        name="word_ids")

        # shape = (batch size)
        self.sequence_lengths = tf.placeholder(tf.int32, shape=[None],
                        name="sequence_lengths")

        # shape = (batch size, max length of sentence, max length of word)
        self.char_ids = tf.placeholder(tf.int32, shape=[None, None, None],
                        name="char_ids")

        # shape = (batch_size, max_length of sentence)
        self.word_lengths = tf.placeholder(tf.int32, shape=[None, None],
                        name="word_lengths")

        # shape = (batch size, max length of sentence in batch)
        self.labels = tf.placeholder(tf.int32, shape=[None, None],
                        name="labels")

        # hyper parameters
        self.dropout = tf.placeholder(dtype=tf.float32, shape=[],
                        name="dropout")
        self.lr = tf.placeholder(dtype=tf.float32, shape=[],
                        name="lr")

    def get_feed_dict(self, words, labels=None, lr=None, dropout=None):
        """Given some data, pad it and build a feed dictionary

        Args:
            words: list of sentences. A sentence is a list of ids of a list of
                words. A word is a list of ids
            labels: list of ids
            lr: (float) learning rate
            dropout: (float) keep prob

        Returns:
            dict {placeholder: value}

        """
        # perform padding of the given data
        
        word_ids, sequence_lengths = pad_sequences(words, 0)

        # build feed dictionary

        print("---------word_ids----------")
       # print(word_ids)
        print("---------sequence_len----------")
        #print(sequence_lengths)

        f = open("/Users/choichangho/NLP2018/korea_univ_nlp_class/data/words.txt", 'r')
        data = f.read()
        f.close()
        words_data = data.split("\n")
        #print(words_data)


        char_ids = []
        word_len = []
        mx_len = 0

        for i in word_ids:
            for j in i:
                num = int(j)
                if(num!= 0):
                    word = words_data[num]
                    mx_len = max(mx_len, len(word))

        print("---------mx_len-----------")
        print(mx_len)

        for i in word_ids:
            char = []
            chlen = []

            for j in i:
                num = int(j)
                word_vector = []
                chlen.append(len(word))
                if (num == 0):
                    for tt in range(mx_len):
                        word_vector.append(0)

                else:
                    word = words_data[num]
                    for k in word:
                        word_vector.append(22217 - 33 + ord(k))
                    while(len(word_vector) < mx_len):
                        word_vector.append(0)

                if(len(word_vector) != 17):
                    print("===================")
                    print(len(word_vector))
                char.append(word_vector)

            if(len(char) != 40):
                print("__________________")
                print(len(char))

            print(len(chlen))

            char_ids.append(char)
            word_len.append(chlen)

        #print("-------------------")
        #print(char_ids)
        #print(word_len)

        feed = {
            self.word_ids: word_ids,
            self.sequence_lengths: sequence_lengths,
            self.char_ids: char_ids,
            self.word_lengths: word_len,
        }


        if labels is not None:
            labels, _ = pad_sequences(labels, 0)
            feed[self.labels] = labels

        if lr is not None:
            feed[self.lr] = lr

        if dropout is not None:
            feed[self.dropout] = dropout

        return feed, sequence_lengths

    def add_word_embeddings_op(self):
        with tf.variable_scope("words"):
            if self.config.embeddings is None:
                self.logger.info("WARNING: randomly initializing word vectors")
                _word_embeddings = tf.get_variable(
                        name="_word_embeddings",
                        dtype=tf.float32,
                        shape=[self.config.nwords, self.config.dim_word])
            else:
                _word_embeddings = tf.Variable(
                        self.config.embeddings,
                        name="_word_embeddings",
                        dtype=tf.float32,
                        trainable=self.config.train_embeddings)

            word_embeddings = tf.nn.embedding_lookup(_word_embeddings,
                    self.word_ids, name="word_embeddings")
            
            # shape = (batch_size, max length of sentence in batch, word dimension)
            self.word_embeddings =  tf.nn.dropout(word_embeddings, self.dropout)

        with tf.variable_scope('char'):
            _char_embeddings = tf.Variable(
                self.config.embeddings,
                name="_char_embeddings",
                dtype=tf.float32,
                trainable=self.config.train_embeddings)

            char_embeddings = tf.nn.embedding_lookup(_char_embeddings,
                                                     self.char_ids, name="char_embeddings")
            self.char_embeddings = tf.nn.dropout(char_embeddings, self.dropout)

    def add_logits_op(self):
        """Defines self.logits

        For each word in each sentence of the batch, it corresponds to a vector
        of scores, of dimension equal to the number of tags.
        """
        with tf.variable_scope("word-lstm", reuse=tf.AUTO_REUSE):
            fw_cell = tf.contrib.rnn.LSTMCell(self.config.hidden_size_lstm)
            bf_cell = tf.contrib.rnn.LSTMCell(self.config.hidden_size_lstm)
            Wc = tf.get_variable("Wc", dtype=tf.float32,
                                 shape=[2 * (self.config.hidden_size_lstm), self.config.hidden_size_char])
            bc = tf.get_variable("bc", shape=[self.config.hidden_size_char], dtype=tf.float32,
                                 initializer=tf.zeros_initializer())
        for i in range(self.config.batch_size):
                (fw_output, bw_output), _ = tf.nn.bidirectional_dynamic_rnn(
                    fw_cell, bf_cell, self.char_embeddings[i], sequence_length= self.word_lengths[i], dtype=tf.float32)
                char_rnn_output = tf.concat([fw_output[self.config.hidden_size_lstm-1], bw_output[self.config.hidden_size_lstm-1]], -1)
                char_rnn_output = tf.matmul(char_rnn_output, Wc) + bc
                if(i==0):
                    char_output = [char_rnn_output]

                else:
                    char_output = tf.concat([char_output,[char_rnn_output]], 0)
            #char_output = tf.transpose(char_output)

        with tf.variable_scope("bi-lstm"):
            cell_fw = tf.contrib.rnn.LSTMCell(self.config.hidden_size_lstm)
            cell_bw = tf.contrib.rnn.LSTMCell(self.config.hidden_size_lstm)
            (output_fw, output_bw), _ = tf.nn.bidirectional_dynamic_rnn(
                    cell_fw, cell_bw, self.word_embeddings,
                    sequence_length=self.sequence_lengths, dtype=tf.float32)
            output = tf.concat([output_fw, output_bw], axis=-1)
            output = tf.nn.dropout(output, self.dropout)

        with tf.variable_scope("proj"):
            W = tf.get_variable("W", dtype=tf.float32,
                    shape=[2*(self.config.hidden_size_lstm+self.config.hidden_size_char), self.config.ntags])

            b = tf.get_variable("b", shape=[self.config.ntags],
                    dtype=tf.float32, initializer=tf.zeros_initializer())
            print('----------output shape--------')
            print(output)
            print('----------char output shape-------')
            print(char_output)
            output = tf.concat([output, char_output], -1)
            nsteps = tf.shape(output)[1]
            output = tf.reshape(output, [-1, 2*(self.config.hidden_size_lstm+self.config.hidden_size_char)])
            pred = tf.matmul(output, W) + b
            self.logits = tf.reshape(pred, [-1, nsteps, self.config.ntags])
            self.labels_pred = tf.cast(tf.argmax(self.logits, axis=-1),
                                       tf.int32)

    def add_pred_op(self):
        """Defines self.labels_pred

        This op is defined only in the case where we don't use a CRF since in
        that case we can make the prediction "in the graph" (thanks to tf
        functions in other words). With theCRF, as the inference is coded
        in python and not in pure tensroflow, we have to make the prediciton
        outside the graph.
        """
        if not self.config.use_crf:
            self.labels_pred = tf.cast(tf.argmax(self.logits, axis=-1),
                    tf.int32)


    def add_loss_op(self):
        
        losses = tf.nn.sparse_softmax_cross_entropy_with_logits(
                logits=self.logits, labels=self.labels)
        mask = tf.sequence_mask(self.sequence_lengths)
        losses = tf.boolean_mask(losses, mask)
        self.loss = tf.reduce_mean(losses)
        # for tensorboard
        tf.summary.scalar("loss", self.loss)

    def build(self):
        # NER specific functions
        self.add_placeholders()
        self.add_word_embeddings_op()
        self.add_logits_op()
        self.add_pred_op()
        self.add_loss_op()

        # Generic functions that add training op and initialize session
        self.add_train_op(self.config.lr_method, self.lr, self.loss,
                self.config.clip)#adam optimizer, learning rate: 0.001, softmax_cross_entropy, clip = -1
        self.initialize_session() # now self.sess is defined and vars are init


    def predict_batch(self, words):
        """
        Args:
            words: list of sentences

        Returns:
            labels_pred: list of labels for each sentence
            sequence_length

        """
        fd, sequence_lengths = self.get_feed_dict(words, dropout=1.0)
        
        labels_pred = self.sess.run(self.labels_pred, feed_dict=fd)

        return labels_pred, sequence_lengths


    def run_epoch(self, train, dev, epoch):
        """Performs one complete pass over the train set and evaluate on dev

        Args:
            train: dataset that yields tuple of sentences, tags
            dev: dataset
            epoch: (int) index of the current epoch

        Returns:
            f1: (python float), score to select model on, higher is better

        """
        # progbar stuff for logging
        batch_size = self.config.batch_size
        nbatches = (len(train) + batch_size - 1) // batch_size
        prog = Progbar(target=nbatches)

        # iterate over dataset
        for i, (words, labels) in enumerate(minibatches(train, batch_size)):
            fd, _ = self.get_feed_dict(words, labels, self.config.lr,
                    self.config.dropout)

            _, train_loss, summary = self.sess.run(
                    [self.train_op, self.loss, self.merged], feed_dict=fd)

            prog.update(i + 1, [("train loss", train_loss)])

            # tensorboard
            if i % 10 == 0:
                self.file_writer.add_summary(summary, epoch*nbatches + i)

        metrics = self.run_evaluate(dev)
        msg = " - ".join(["{} {:04.2f}".format(k, v)
                for k, v in metrics.items()])
        self.logger.info(msg)

        return metrics["f1"]


    def run_evaluate(self, test):
        """Evaluates performance on test set

        Args:
            test: dataset that yields tuple of (sentences, tags)

        Returns:
            metrics: (dict) metrics["acc"] = 98.4, ...

        """
        accs = []
        correct_preds, total_correct, total_preds = 0., 0., 0.
        for words, labels in minibatches(test, self.config.batch_size):
            labels_pred, sequence_lengths = self.predict_batch(words)

            for lab, lab_pred, length in zip(labels, labels_pred,
                                             sequence_lengths):
                lab      = lab[:length]
                lab_pred = lab_pred[:length]
                accs    += [a==b for (a, b) in zip(lab, lab_pred)]

                lab_chunks      = set(get_chunks(lab, self.config.vocab_tags))
                lab_pred_chunks = set(get_chunks(lab_pred,
                                                 self.config.vocab_tags))

                correct_preds += len(lab_chunks & lab_pred_chunks)
                total_preds   += len(lab_pred_chunks)
                total_correct += len(lab_chunks)

        p   = correct_preds / total_preds if correct_preds > 0 else 0
        r   = correct_preds / total_correct if correct_preds > 0 else 0
        f1  = 2 * p * r / (p + r) if correct_preds > 0 else 0
        acc = np.mean(accs)

        return {"acc": 100*acc, "f1": 100*f1}


    def predict(self, words_raw):
        """Returns list of tags

        Args:
            words_raw: list of words (string), just one sentence (no batch)

        Returns:
            preds: list of tags (string), one for each word in the sentence

        """
        words = [self.config.processing_word(w) for w in words_raw]
        if type(words[0]) == tuple:
            words = zip(*words)
        pred_ids, _ = self.predict_batch([words])
        preds = [self.idx_to_tag[idx] for idx in list(pred_ids[0])]

        return preds
