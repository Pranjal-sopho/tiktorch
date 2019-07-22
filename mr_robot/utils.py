# utility functions for the robot
import numpy as np
from scipy.ndimage import convolve
import seaborn as sn
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import confusion_matrix


# ref: https://github.com/constantinpape/vis_tools/blob/master/vis_tools/edges.py#L5
def make_edges3d(segmentation):
    """ Make 3d edge volume from 3d segmentation
    """
    # NOTE we add one here to make sure that we don't have zero in the segmentation
    gz = convolve(segmentation + 1, np.array([-1.0, 0.0, 1.0]).reshape(3, 1, 1))
    gy = convolve(segmentation + 1, np.array([-1.0, 0.0, 1.0]).reshape(1, 3, 1))
    gx = convolve(segmentation + 1, np.array([-1.0, 0.0, 1.0]).reshape(1, 1, 3))
    return (gx ** 2 + gy ** 2 + gz ** 2) > 0


n = 0
block_list, idx_list, visited = [], [], {}


def recursive_chop(dim_number, arr_shape, block_shape):
    global block_list, idx_list, visited

    if dim_number >= n:
        return

    for i in range(0, arr_shape[dim_number], block_shape[dim_number]):
        idx_list[dim_number] = i
        recursive_chop(dim_number + 1, arr_shape, block_shape)
        slice_list, visited_key = [], []

        for j in range(n):
            visited_key.append(idx_list[j])
            if idx_list[j] + block_shape[j] > arr_shape[j]:
                slice_list.append(slice(arr_shape[j] - block_shape[j], arr_shape[j]))
            else:
                slice_list.append(slice(idx_list[j], idx_list[j] + block_shape[j]))

        visited_key = tuple(visited_key)
        if visited.get(visited_key) == None:
            visited[visited_key] = 1
            block_list.append(tuple(slice_list))

    idx_list[dim_number] = 0


def tile_image(arr_shape, block_shape):
    """
    chops of blocks of given size from an array 

    Args:
    arr_shape(tuple): size of input array (ndarray)
    block_shape (tuple): size of block to cut into (ndarray)

    Return type: list(tuple(slice()))- a list of tuples, one per block where each tuple has
    n slice objects, one per dimension (n: number of dimensions)
    """

    assert len(arr_shape) == len(block_shape), "block shape not compatible with array shape"
    for i in range(len(arr_shape)):
        assert arr_shape[i] >= block_shape[i], "block shape not compatible with array shape"

    global n, idx_list, visited
    n = len(arr_shape)
    block_list.clear(), visited.clear()
    idx_list = [0 for i in range(n)]

    recursive_chop(0, arr_shape, block_shape)
    return block_list


def get_confusion_matrix(pred_labels, act_labels, cls_dict):

    act_labels_f = [str(i) for i in act_labels.tolist()]
    pred_labels_f = [str(i) for i in pred_labels.tolist()]

    c_mat_arr = confusion_matrix(act_labels_f, pred_labels_f, labels=[str(i) for i in cls_dict.keys()])
    c_mat_n = c_mat_arr / c_mat_arr.astype(np.float).sum(axis=1, keepdims=True)
    # c_mat_n = c_mat_arr / np.expand_dims(np.sum(c_mat_arr, axis=1), axis=1)

    return c_mat_n


def plot_confusion_matrix(c_mat_n, cls_dict):

    pd_cm_n = pd.DataFrame(
        c_mat_n, index=[str(i) for i in cls_dict.values()], columns=[str(i) for i in cls_dict.values()]
    )

    sn_plot_n = sn.heatmap(pd_cm_n, annot=True)
    return sn_plot_n.figure


def integer_to_onehot(integer_maps):
    return np.stack(
        [integer_maps == integer for integer in range(integer_maps.min(), integer_maps.max() + 1)], axis=0
    ).astype(np.uint8)


def onehot_preds_to_integer(one_hot_preds):
    return np.argmax(one_hot_preds, axis=0)


def get_coordinate(block):
    """ return the starting co-ordinate of a block

    Args:
    block(tuple): tuple of slice objects, one per dimension
    """

    coordinate = []
    for slice_ in block:
        coordinate.append(slice_.start)

    return tuple(coordinate)


def get_random_index(canvas_shape):
    random_index = []
    for i in range(len(canvas_shape)):
        random_index.append(np.random.randint(0, canvas_shape[i]))

    return tuple(random_index)


def get_random_patch(canvas_shape):
    rand_index = get_random_index(canvas_shape)
    patch_dimension = []
    for i in range(len(canvas_shape)):
        patch_dimension.append(np.random.randint(1, canvas_shape[i] - rand_index[i] + 1))

    block = []
    for i in range(len(patch_dimension)):
        block.append(slice(rand_index[i], rand_index[i] + patch_dimension[i]))
    return tuple(block)
