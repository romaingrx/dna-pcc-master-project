#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author : Romain Graux
@date : 2022 May 13, 11:24:49
@last modified : 2022 May 16, 15:13:44
"""

import logging
from tqdm import tqdm
import tensorflow as tf
from src import pc_io, processing

logger = logging.getLogger(__name__)


def dir_to_ds(input_dir, resolution, channels_last):
    """Load all point clouds from the input_dir and transform them to a tensorflow dataset."""
    # Load the point clouds
    files = pc_io.get_files(input_dir)
    # Load the blocks from the files.
    p_min, p_max, dense_tensor_shape = pc_io.get_shape_data(resolution, channels_last)
    points = pc_io.load_points(files, p_min, p_max)

    with tf.device("CPU"):
        logger.info("Transforming the point clouds to tensors")
        points = [
            processing.pc_to_tf(pc, dense_tensor_shape, channels_last)
            for pc in tqdm(points)
        ]

        # Convert the sparse tensors to dense tensors.
        logger.info("Transforming the sparse tensors to dense ones")
        points = [processing.process_x(pc, dense_tensor_shape) for pc in tqdm(points)]

    # Create a tensorflow dataset from the point clouds.
    ds = tf.data.Dataset.from_tensor_slices(points)
    return ds


def number_of_nucleotides(x):
    """Return the number of nucleotides in the latent space."""
    # In general all oligos are the same length (200) but it is preferable to compute the number of nucleotides with the length of each one.
    return tf.reduce_sum(
        [
            [[len(oligo.numpy()) for oligo in channel] for channel in batch]
            for batch in x
        ]
    )


def train_test_split_ds(ds, validation_split=0.2, test_split=0.0):
    assert 0 <= validation_split <= 1, "validation_split must be between 0 and 1"
    assert 0 <= test_split <= 1, "test_split must be between 0 and 1"
    assert (
        validation_split + test_split <= 1
    ), "validation_split + test_split must be less than 1"

    n = ds.cardinality().numpy()

    validation_size = int(n * validation_split)
    test_size = int(n * test_split)
    train_size = max(n - test_size - validation_size, 0)

    train_ds = ds.take(train_size)
    validation_ds = ds.skip(train_size)

    if test_split > 0:
        test_ds = validation_ds.skip(validation_size)
        validation_ds = validation_ds.take(validation_size)
        return train_ds, validation_ds, test_ds
    return train_ds, validation_ds