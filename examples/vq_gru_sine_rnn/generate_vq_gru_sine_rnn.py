import matplotlib
matplotlib.use("Agg")

import argparse
import tensorflow as tf
import numpy as np
from tfbldr.datasets import make_sinewaves
from collections import namedtuple, defaultdict
import sys
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('direct_model', nargs=1, default=None)
parser.add_argument('--model', dest='model_path', type=str, default=None)
parser.add_argument('--seed', dest='seed', type=int, default=1999)
args = parser.parse_args()
if args.model_path == None:
    if args.direct_model == None:
        raise ValueError("Must pass first positional argument as model, or --model argument, e.g. summary/experiment-0/models/model-7")
    else:
        model_path = args.direct_model[0]
else:
    model_path = args.model_path

sines = make_sinewaves(50, 40, harmonic=True)
train_sines = sines[:, ::2]
train_sines = [train_sines[:, i] for i in range(train_sines.shape[1])]
valid_sines = sines[:, 1::2]
valid_sines = [valid_sines[:, i] for i in range(valid_sines.shape[1])]

random_state = np.random.RandomState(args.seed)

"""
config = tf.ConfigProto(
    device_count={'GPU': 0}
)
"""

n_hid = 128
batch_size = 10
prime = 20

#with tf.Session(config=config) as sess:
with tf.Session() as sess:
    saver = tf.train.import_meta_graph(model_path + '.meta')
    saver.restore(sess, model_path)
    fields = ["inputs",
              "inputs_tm1",
              "inputs_t",
              "init_q_hidden",
              "q_hiddens",
              "q_nvq_hiddens",
              "i_hiddens",
              "pred",
              "loss",
              "rec_loss",
              "train_step"]
    vs = namedtuple('Params', fields)(
        *[tf.get_collection(name)[0] for name in fields]
    )
    x = np.array(valid_sines)
    x = x.transpose(1, 0, 2)
    prev_x_full = x[:prime, :batch_size]
    res = []
    q_res = []
    i_res = []
    init_q_h = np.zeros((batch_size, n_hid)).astype("float32")
    for i in range(50):
        if i < prime:
            prev_x = prev_x_full[i][None]
        feed = {vs.inputs_tm1: prev_x[:1],
                vs.init_q_hidden: init_q_h}
        outs = [vs.pred, vs.q_hiddens, vs.i_hiddens]
        r = sess.run(outs, feed_dict=feed)

        prev_x = r[0]
        q_hids = r[1]
        i_hids = r[2]
        init_q_h = q_hids[0]
        if i < prime:
            res.append(prev_x_full[i][None])
        else:
            res.append(prev_x)
        q_res.append(q_hids)
        i_res.append(i_hids)
    o = np.concatenate(res, axis=0)[:, :, 0]
    ind = np.concatenate(i_res, axis=0)

    f, axarr = plt.subplots(11, 1)
    for i in range(10):
        if i % 2 == 0:
            x = np.arange(len(o[:, i // 2]))
            axarr[i].plot(x, o[:, i // 2], color="steelblue")
        else:
            for n in range(ind.shape[2]):
                axarr[i].plot(x[prime:], ind[prime:, i // 2, n])
            for n in range(ind.shape[2]):
                axarr[i].plot(x[:prime], ind[:prime, i // 2, n], alpha=0.2)

    axarr[-1].plot(valid_sines[0][1:, 0], color="forestgreen")

    plt.savefig("results")
    plt.close()
