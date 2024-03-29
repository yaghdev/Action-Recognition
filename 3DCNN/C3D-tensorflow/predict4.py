 
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path
import time
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf
import input_data
import c3d_model
import numpy as np

# Basic model parameters as external flags.
flags = tf.app.flags
gpu_num = 2
#flags.DEFINE_integer('batch_size', 10 , 'Batch size.')
FLAGS = flags.FLAGS

def placeholder_inputs(batch_size):
 
  images_placeholder = tf.placeholder(tf.float32, shape=(batch_size,
                                                         c3d_model.NUM_FRAMES_PER_CLIP,
                                                         c3d_model.CROP_SIZE,
                                                         c3d_model.CROP_SIZE,
                                                         c3d_model.CHANNELS))
  labels_placeholder = tf.placeholder(tf.int64, shape=(batch_size))
  return images_placeholder, labels_placeholder

def _variable_on_cpu(name, shape, initializer):
  #with tf.device('/cpu:%d' % cpu_id):
  with tf.device('/cpu:0'):
    var = tf.get_variable(name, shape, initializer=initializer)
  return var

def _variable_with_weight_decay(name, shape, stddev, wd):
  var = _variable_on_cpu(name, shape, tf.truncated_normal_initializer(stddev=stddev))
  if wd is not None:
    weight_decay = tf.nn.l2_loss(var) * wd
    tf.add_to_collection('losses', weight_decay)
  return var



def run_test():
    tf.reset_default_graph()
    init_path = 'D:/autism/3DCNN-master/c3d_ucf_model-2520'
    for i in os.listdir(init_path):
        model_name = init_path+'/'+'c3d_ucf_model-2520'
        print(model_name)
        test_list_file = 'D:/autism/3DCNN-master/C3D-tensorflow/list/test_list.list'
        num_test_videos = len(list(open(test_list_file,'r')))
        print("Number of test videos={}".format(num_test_videos))
        
          # Get the sets of images and labels for training, validation, and
        images_placeholder, labels_placeholder = placeholder_inputs(FLAGS.batch_size * gpu_num)
        with tf.variable_scope('var_name') as var_scope:
            weights = {

                    'wc1': _variable_with_weight_decay('wc1', [3, 3, 3, 3, 64], 0.04, 0.00),
                    'wc2': _variable_with_weight_decay('wc2', [3, 3, 3, 64, 128], 0.04, 0.00),
                    'wc3a': _variable_with_weight_decay('wc3a', [3, 3, 3, 128, 256], 0.04, 0.00),
                    'wc3b': _variable_with_weight_decay('wc3b', [3, 3, 3, 256, 256], 0.04, 0.00),
                    'wc4a': _variable_with_weight_decay('wc4a', [3, 3, 3, 256, 512], 0.04, 0.00),
                    'wc4b': _variable_with_weight_decay('wc4b', [3, 3, 3, 512, 512], 0.04, 0.00),
                    'wc5a': _variable_with_weight_decay('wc5a', [3, 3, 3, 512, 512], 0.04, 0.00),
                    'wc5b': _variable_with_weight_decay('wc5b', [3, 3, 3, 512, 512], 0.04, 0.00),
                    'wd1': _variable_with_weight_decay('wd1', [8192, 4096], 0.04, 0.001),
                    'wd2': _variable_with_weight_decay('wd2', [4096, 4096], 0.04, 0.002),
                    'out': _variable_with_weight_decay('wout', [4096, 8], 0.04, 0.005)
                    }
            biases = {
                    'bc1': _variable_with_weight_decay('bc1', [64], 0.04, 0.0),
                    'bc2': _variable_with_weight_decay('bc2', [128], 0.04, 0.0),
                    'bc3a': _variable_with_weight_decay('bc3a', [256], 0.04, 0.0),
                    'bc3b': _variable_with_weight_decay('bc3b', [256], 0.04, 0.0),
                    'bc4a': _variable_with_weight_decay('bc4a', [512], 0.04, 0.0),
                    'bc4b': _variable_with_weight_decay('bc4b', [512], 0.04, 0.0),
                    'bc5a': _variable_with_weight_decay('bc5a', [512], 0.04, 0.0),
                    'bc5b': _variable_with_weight_decay('bc5b', [512], 0.04, 0.0),
                    'bd1': _variable_with_weight_decay('bd1', [4096], 0.04, 0.0),
                    'bd2': _variable_with_weight_decay('bd2', [4096], 0.04, 0.0),
                    'out': _variable_with_weight_decay('bout', [8], 0.04, 0.0),
                    }
        logits = []
        for gpu_index in range(0, gpu_num):
            with tf.device('/gpu:%d' % gpu_index):
                logit = c3d_model.inference_c3d(images_placeholder[gpu_index * FLAGS.batch_size:(gpu_index + 1) * FLAGS.batch_size,:,:,:,:], 0.6, FLAGS.batch_size, weights, biases)
                logits.append(logit)
        logits = tf.concat(logits,0)
        norm_score = tf.nn.softmax(logits)
        saver = tf.train.Saver()
        sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
        init = tf.global_variables_initializer()
        sess.run(init)
         # Create a saver for writing training checkpoints.
        saver.restore(sess, model_name)
          # And then after everything is built, start the training loop.
        bufsize = 0
        write_file = open("D:/autism/3DCNN-master/predict_"+str(i)+".txt", "w+")
        next_start_pos = -1
        all_steps = int((num_test_videos - 1) / (FLAGS.batch_size * gpu_num) + 1)
        for step in xrange(all_steps):
          
            start_time = time.time()
            test_images, test_labels, next_start_pos, _, valid_len = \
            input_data.read_clip_and_label(
                    test_list_file, FLAGS.batch_size * gpu_num, start_pos=next_start_pos
                )
            
            #print(test_images[0],test_labels[0])
            predict_score = norm_score.eval(
                    session=sess,
                    feed_dict={images_placeholder: test_images}
                    )
            for i in range(0, valid_len):
              true_label = test_labels[i],
              top1_predicted_label = np.argmax(predict_score[i])
              # Write results: true label, class prob for true label, predicted label, class prob for predicted label
              write_file.write('{}, {}, {}, {}\n'.format(
                      true_label[0],
                      predict_score[i][true_label],
                      top1_predicted_label,
                      predict_score[i][top1_predicted_label]))
        write_file.close()
        print("done for "+ str(i))
       
    

def main(_):
  run_test()

if __name__ == '__main__':
  tf.app.run()

