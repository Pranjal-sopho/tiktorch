import numpy
import pytest
import torch
from torch import multiprocessing as mp

from tiktorch.configkeys import TRAINING, TRAINING_SHAPE, TRAINING_SHAPE_UPPER_BOUND
from tiktorch.rpc.mp import Shutdown, create_client
from tiktorch.server.handler.handler import HandlerProcess, IHandler
from tiktorch.server.handler.handler import run as run_handler
from tiktorch.tiktypes import TikTensor, TikTensorBatch


@pytest.fixture
def handler2d(tiny_model_2d, log_queue):
    hp = HandlerProcess(**tiny_model_2d, log_queue=log_queue)
    hp.set_devices(["cpu"])
    yield hp
    hp.shutdown()


@pytest.fixture
def handler3d(tiny_model_3d, log_queue):
    hp = HandlerProcess(**tiny_model_3d, log_queue=log_queue)
    hp.set_devices(["cpu"])
    yield hp
    hp.shutdown()


@pytest.fixture
def client2d(tiny_model_2d, log_queue):
    client_conn, handler_conn = mp.Pipe()

    p = mp.Process(
        target=run_handler, name="Handler", kwargs={"conn": handler_conn, **tiny_model_2d, "log_queue": log_queue}
    )
    p.start()

    cl = create_client(IHandler, client_conn)
    cl.set_devices(["cpu"])
    yield cl

    cl.shutdown.async_().result(timeout=30)
    p.join(timeout=20)


@pytest.fixture
def client3d(tiny_model_3d, log_queue):
    client_conn, handler_conn = mp.Pipe()

    p = mp.Process(
        target=run_handler, name="Handler", kwargs={"conn": handler_conn, **tiny_model_3d, "log_queue": log_queue}
    )
    p.start()

    cl = create_client(IHandler, client_conn)
    cl.set_devices(["cpu"])
    yield cl

    cl.shutdown.async_().result(timeout=30)
    p.join(timeout=20)


def test_initialization(handler2d):
    active_children = handler2d.active_children()

    assert "Training" in active_children
    assert "Inference" in active_children
    assert "DryRun" in active_children


def test_initialization_through_client(client2d):
    children = client2d.active_children()
    assert "DryRun" in children
    assert "Inference" in children
    assert "Training" in children


def test_forward_2d(handler2d, tiny_model_2d):
    C, Y, X = tiny_model_2d["config"]["input_channels"], 15, 15
    futs = []
    for data in [
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
    ]:
        futs.append(handler2d.forward(data))

    for i, fut in enumerate(futs):
        fut.result(timeout=30)
        print(f"got fut {i + 1}/{len(futs)}", flush=True)


def test_forward_2d_through_client(client2d, tiny_model_2d):
    C, Y, X = tiny_model_2d["config"]["input_channels"], 15, 15
    futs = []
    for data in [
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Y, X)).astype(numpy.float32)),
    ]:
        futs.append(client2d.forward(data))

    for i, fut in enumerate(futs):
        fut.result(timeout=30)
        print(f"got fut {i + 1}/{len(futs)}", flush=True)


def test_forward_3d(handler3d, tiny_model_3d):
    C, Z, Y, X = tiny_model_3d["config"]["input_channels"], 15, 15, 15
    futs = []
    for data in [
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
    ]:
        futs.append(handler3d.forward(data))

    for i, fut in enumerate(futs):
        fut.result(timeout=30)
        print(f"got fut {i + 1}/{len(futs)}", flush=True)


def test_forward_3d_through_client(client3d, tiny_model_3d):
    C, Z, Y, X = tiny_model_3d["config"]["input_channels"], 15, 15, 15
    futs = []
    for data in [
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
        TikTensor(numpy.random.random((C, Z, Y, X)).astype(numpy.float32)),
    ]:
        futs.append(client3d.forward(data))

    for i, fut in enumerate(futs):
        fut.result(timeout=30)
        print(f"got fut {i + 1}/{len(futs)}", flush=True)


def test_dry_run(handler3d, tiny_model_3d):
    input_channels = tiny_model_3d["config"]["input_channels"]
    handler3d.update_config(
        {TRAINING: {TRAINING_SHAPE_UPPER_BOUND: [input_channels, 14, 43, 47], TRAINING_SHAPE: None}}
    )
    approved_devices, training_shape, valid_shapes, shrinkage = handler3d.dry_run.dry_run(
        devices=[torch.device("cpu")]
    ).result(timeout=30)
    assert len(approved_devices) == 1
    for expected, received in zip([input_channels, 14, 43, 47], training_shape):
        assert expected == received, training_shape

    assert len(valid_shapes) >= 1


def test_dry_run_through_handler(handler3d, tiny_model_3d):
    input_channels = tiny_model_3d["config"]["input_channels"]
    handler3d.update_config(
        {TRAINING: {TRAINING_SHAPE_UPPER_BOUND: [input_channels, 14, 43, 47], TRAINING_SHAPE: None}}
    )
    training_shape, valid_shapes, shrinkage = handler3d.set_devices(device_names=["cpu"]).result(timeout=30)

    for expected, received in zip([input_channels, 14, 43, 47], training_shape):
        assert expected == received, training_shape

    assert len(valid_shapes) >= 1
