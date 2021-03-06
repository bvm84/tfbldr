import argparse
import tensorflow as tf
import numpy as np
from tfbldr.datasets import piano_roll_imlike_to_image_array
from tfbldr.datasets import save_image_array
from tfbldr.datasets import notes_to_midi
from tfbldr.datasets import midi_to_notes
from collections import namedtuple
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import copy
from tfbldr.datasets import quantized_to_pretty_midi
import os

from decode import decode_measure

parser = argparse.ArgumentParser()
parser.add_argument('pixelcnn_model', nargs=1, default=None)
parser.add_argument('vqvae_model', nargs=1, default=None)
parser.add_argument('--seed', dest='seed', type=int, default=1999)
parser.add_argument('--temp', dest='temp', type=float, default=1.)
parser.add_argument('--chords', dest='chords', type=str, default=None)
args = parser.parse_args()
vqvae_model_path = args.vqvae_model[0]
pixelcnn_model_path = args.pixelcnn_model[0]

num_to_generate = 1000
num_each = 64
random_state = np.random.RandomState(args.seed)

d1 = np.load("music_data_jos_pianoroll_multichannel.npz")
flat_images = np.array([mai for amai in copy.deepcopy(d1['measures_as_images']) for mai in amai])
image_data = flat_images

# times 0 to ensure NO information leakage
sample_image_data = 0. * image_data
# shuffle it just because
random_state.shuffle(sample_image_data)

d2 = np.load("vq_vae_encoded_music_jos_2d_pianoroll_multichannel.npz")

# use these to generate
labels = d2["labels"]
flat_idx = d2["flat_idx"]
labelnames = d2["labelnames"]
sample_labels = labels[-1000:]
sample_labelnames = labelnames[-1000:]

full_chords_kv = d2["full_chords_kv"]
label_to_lcr_kv = d2["label_to_lcr_kv"]
basic_chords_kv = d2["basic_chords_kv"]
full_chords_kv = d2["full_chords_kv"]

label_to_lcr = {int(k): tuple([int(iv) for iv in v.split(",")]) for k, v in label_to_lcr_kv}
lcr_to_label = {v: k for k, v in label_to_lcr.items()}

full_chords_lu = {k: int(v) for k, v in full_chords_kv}
full_chords_lu_inv = {v: k for k, v in full_chords_lu.items()}

basic_chords_lu = {k: int(v) for k, v in basic_chords_kv}
basic_chords_lu_inv = {v: k for k, v in basic_chords_lu.items()}

if args.chords != None:
    raise ValueError("")
    chordseq = args.chords.split(",")
    if len(chordseq) < 3:
        raise ValueError("Provided chords length < 3, need at least 3 chords separated by spaces! Example: --chords=I7,IV7,V7,I7 . Got {}".format(args.chords))
    ch =  [cs for cs in args.chords.split(",")]
    clbl = [full_chords_lu[cs] for cs in ch]
    stretched = clbl * (num_to_generate // len(clbl) + 1)
    sample_labels = np.array(stretched[:len(sample_labels)])[:, None]

def sample_gumbel(logits, temperature=args.temp):
    noise = random_state.uniform(1E-5, 1. - 1E-5, np.shape(logits))
    return np.argmax((logits - logits.max() - 1) / float(temperature) - np.log(-np.log(noise)), axis=-1)

config = tf.ConfigProto(
    device_count={'GPU': 0}
)

with tf.Session(config=config) as sess1:
    saver = tf.train.import_meta_graph(pixelcnn_model_path + '.meta')
    saver.restore(sess1, pixelcnn_model_path)
    fields = ['images',
              'labels',
              'x_tilde']
    vs = namedtuple('Params', fields)(
        *[tf.get_collection(name)[0] for name in fields]
    )
    y = sample_labels[:num_to_generate]

    pix_z = np.zeros((num_to_generate, 12, 6))
    for i in range(pix_z.shape[1]):
        for j in range(pix_z.shape[2]):
            print("Sampling v completion pixel {}, {}".format(i, j))
            feed = {vs.images: pix_z[..., None],
                    vs.labels: y}
            outs = [vs.x_tilde]
            r = sess1.run(outs, feed_dict=feed)
            x_rec = sample_gumbel(r[-1])

            for k in range(pix_z.shape[0]):
                pix_z[k, i, j] = float(x_rec[k, i, j])
sess1.close()
tf.reset_default_graph()

with tf.Session(config=config) as sess2:
    saver = tf.train.import_meta_graph(vqvae_model_path + '.meta')
    saver.restore(sess2, vqvae_model_path)
    """
    # test by faking like we sampled these from pixelcnn
    d = np.load("vq_vae_encoded_mnist.npz")
    valid_z_i = d["valid_z_i"]
    """
    fields = ['images',
              'bn_flag',
              'z_e_x',
              'z_q_x',
              'z_i_x',
              'x_tilde']
    vs = namedtuple('Params', fields)(
        *[tf.get_collection(name)[0] for name in fields]
    )
    x = image_data[:num_to_generate]
    z_i = pix_z[:num_to_generate]
    # again multiply by 0 to avoid information leakage
    feed = {vs.images: 0. * x,
            vs.z_i_x: z_i,
            vs.bn_flag: 1.}
    outs = [vs.x_tilde]
    r = sess2.run(outs, feed_dict=feed)
    x_rec = r[-1]

# binarize the predictions
x_rec[x_rec > 0.5] = 1.
x_rec[x_rec <= 0.5] = 0.

"""
# find some start points
for n in range(len(sample_labels)):
    lcr_i = label_to_lcr[sample_labels[n, 0]]
    if lcr_i[0] == 0:
        print(n) 
"""
# 16 44 117 119 143 151 206 242 267 290 308 354 380 410 421 456 517 573 598 622 638 663 676 688 715 725 749 752 820 851 866 922

# start at 16 since that's the start of a chord sequence (could choose any of the numbers above)
for offset in [16, 44, 308, 421, 517, 752, 866]:
    print("sampling offset {}".format(offset))
    x_rec_i = x_rec[offset:offset + num_each]
    these_labelnames = sample_labelnames[offset:offset + num_each]

    x_ts = piano_roll_imlike_to_image_array(x_rec_i, 0.25)
    # cut off zero padding on the vertical axis

    if not os.path.exists("samples"):
        os.mkdir("samples")

    if args.chords == None:
        save_image_array(x_ts, "samples/pianoroll_multichannel_pixel_cnn_gen_{}_seed_{}_temp_{}.png".format(offset, args.seed, args.temp))
    else:
        save_image_array(x_ts, "samples/pianoroll_multichannel_pixel_cnn_gen_{}_seed_{}_temp_{}.png".format(args.chords, args.seed, args.temp))

    sample_flat_idx = flat_idx[-1000:]

    p = sample_flat_idx[offset:offset + num_each]

    satb_midi = [[], [], [], []]
    satb_notes = [[], [], [], []]
    for n in range(len(x_rec_i)):
        measure_len = x_rec_i[n].shape[1]
        # 96 x 48 measure in
        events = {}
        for v in range(x_rec_i.shape[-1]):
            all_up = zip(*np.where(x_rec_i[n][..., v]))
            time_ordered = [au for i in range(measure_len) for au in all_up if au[1] == i]
            for to in time_ordered:
                if to[1] not in events:
                    # fill with rests
                    events[to[1]] = [0, 0, 0, 0]
                events[to[1]][v] = to[0]
        satb =[[], [], [], []]
        for v in range(x_rec_i.shape[-1]):
            for ts in range(measure_len):
                if ts in events:
                    satb[v].append(events[ts][v])
                else:
                    # edge case if ALL voices rest
                    satb[v].append(0)
        # was ordered btas
        satb = satb[::-1]
        for i in range(len(satb)):
            satb_midi[i].extend(satb[i])
            satb_notes[i].extend(midi_to_notes([satb[i]])[0])

    if args.chords == None:
        name_tag="pianoroll_multichannel_sample_{}_seed_{}_temp_{}".format(offset, args.seed, args.temp) + "_{}.mid"
    else:
        name_tag="pianoroll_multichannel_sample_{}_seed_{}_temp_{}".format(args.chords, args.seed, args.temp) + "_{}.mid"

    np.savez("samples/sample_{}_seed_{}.npz".format(offset, args.seed), pr=x_rec_i, midi=satb_midi, notes=satb_notes, labelnames=these_labelnames)
    quantized_to_pretty_midi([satb_midi],
                             0.25,
                             save_dir="samples",
                             name_tag=name_tag,
                             default_quarter_length=220,
                             voice_params="woodwinds")
    print("saved sample {}".format(offset))
from IPython import embed; embed(); raise ValueError()
