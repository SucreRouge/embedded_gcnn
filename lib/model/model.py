import time

import tensorflow as tf

from .metrics import (softmax_cross_entropy, sigmoid_cross_entropy, total_loss,
                      top_accuracy, threshold_accuracy)


class Model(object):
    def __init__(self,
                 placeholders,
                 name=None,
                 isMultilabel=False,
                 learning_rate=0.001,
                 epsilon=1e-08,
                 train_dir=None,
                 log_dir=None):

        if not name:
            name = self.__class__.__name__.lower()

        self.placeholders = placeholders
        self.name = name
        self.isMultilabel = isMultilabel
        if not isMultilabel:
            self._loss_algorithm = softmax_cross_entropy
        else:
            self._loss_algorithm = sigmoid_cross_entropy

        self.train_dir = train_dir
        self.log_dir = log_dir
        self.logging = False if log_dir is None else True
        self.sess = None

        self.inputs = placeholders['features']
        self.labels = placeholders['labels']
        self.outputs = None

        self.layers = []
        self.vars = {}

        self.optimizer = tf.train.AdamOptimizer(learning_rate, epsilon=epsilon)

        self._loss = None
        self._top_accuracy = None
        self._threshold_accuracy = None
        self._train = None
        self._summary = None
        self._writer = None

        # Create global step variable.
        self._global_step = tf.get_variable(
            '{}/global_step'.format(self.name),
            shape=[],
            dtype=tf.int32,
            initializer=tf.constant_initializer(0, dtype=tf.int32),
            trainable=False)

    def build(self):
        with tf.variable_scope(self.name):
            self._build()

        # Store model variables for saving and loading.
        variables = tf.get_collection(
            tf.GraphKeys.GLOBAL_VARIABLES, scope=self.name)
        self.vars = {var.name: var for var in variables}

        # Call each layer with the previous outputs.
        self.outputs = self.inputs
        for layer in self.layers:
            self.outputs = layer(self.outputs)

        # Build metrics.
        self._loss = self._loss_algorithm(self.outputs, self.labels)
        self._loss = total_loss(self._loss)
        self._top_accuracy = top_accuracy(self.outputs, self.labels)
        if self.isMultilabel:
            self._threshold_accuracy = threshold_accuracy(self.outputs,
                                                          self.labels)

        # Build train op.
        self._train = self.optimizer.minimize(
            self._loss, global_step=self._global_step)

        # Create session.
        self.sess = tf.Session()
        if self.logging:
            if tf.gfile.Exists(self.log_dir):
                tf.gfile.DeleteRecursively(self.log_dir)
            tf.gfile.MakeDirs(self.log_dir)

            self._summary = tf.summary.merge_all()
            self._writer = tf.summary.FileWriter(self.log_dir, self.sess.graph)

    def _build(self):
        raise NotImplementedError

    def initialize(self):
        self.sess.run(tf.global_variables_initializer())

        if self.train_dir is None:
            return self.sess.run(self._global_step)

        if tf.gfile.Exists(self.train_dir):
            saver = tf.train.Saver(self.vars)
            save_path = '{}/checkpoint.ckpt'.format(self.train_dir)
            saver.restore(self.sess, save_path)
            print('Model restored from file {}.'.format(save_path))
        else:
            tf.gfile.MakeDirs(self.train_dir)

        return self.sess.run(self._global_step)

    def save(self):
        if self.train_dir is None:
            return

        saver = tf.train.Saver(self.vars)
        save_path = '{}/checkpoint.ckpt'.format(self.train_dir)
        saver.save(self.sess, save_path)
        print('Model saved in file {}.'.format(save_path))

    def train(self, feed_dict, step=None):
        t = time.time()

        if self.logging:
            _, summary = self.sess.run([self._train, self._summary], feed_dict)
            self._writer.add_summary(summary, step)
        else:
            self.sess.run(self._train, feed_dict)

        return time.time() - t

    def evaluate(self, feed_dict, step=None, name=None):
        if not self.isMultilabel:
            loss, acc = self.sess.run([self._loss, self._top_accuracy],
                                      feed_dict)
            if self.logging and step is not None and name is not None:
                self._add_summary('{}_loss'.format(name), loss, step)
                self._add_summary('{}_accuracy'.format(name), acc, step)
            return loss, acc
        else:
            loss, acc_1, acc_2 = self.sess.run(
                [self._loss, self._top_accuracy, self._threshold_accuracy],
                feed_dict)
            if self.logging and step is not None and name is not None:
                self._add_summary('{}_loss'.format(name), loss, step)
                self._add_summary('{}_top_accuracy'.format(name), acc_1, step)
                self._add_summary('{}_threshold_accuracy'.format(name), acc_2,
                                  step)
            return loss, acc_1, acc_2

    def _add_summary(self, name, value, step):
        summary = tf.Summary(
            value=[tf.Summary.Value(tag=name, simple_value=value)])
        self._writer.add_summary(summary, step)
