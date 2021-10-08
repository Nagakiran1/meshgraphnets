# Lint as: python3
# pylint: disable=g-bad-file-header
# Copyright 2020 DeepMind Technologies Limited. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Functions to build evaluation metrics for cloth data."""

# import tensorflow.compat.v1 as tf
import torch
import common

device = torch.device('cuda')


def _rollout(model, initial_state, num_steps):
    """Rolls out a model trajectory."""
    node_type = initial_state['node_type']
    mask = torch.eq(node_type[:, 0], torch.tensor([common.NodeType.NORMAL.value], device=device))
    mask = torch.stack((mask, mask, mask), dim=1)

    def step_fn(prev_pos, cur_pos, trajectory):
        # memory_prev = torch.cuda.memory_allocated(device) / (1024 * 1024)
        with torch.no_grad():
            prediction = model({**initial_state,
                                'prev|world_pos': prev_pos,
                                'world_pos': cur_pos}, is_training=False)
            '''
            print("prediction")
            print(prediction[10])
            '''
        # memory_next = torch.cuda.memory_allocated(device) / (1024 *1024)
        # print("memory usage", memory_next - memory_prev)
        # don't update kinematic nodes
        '''
        print("prediction shape")
        print(prediction.shape)
        print("cur_pos shape")
        print(cur_pos.shape)
        '''
        next_pos = torch.where(mask, torch.squeeze(prediction), torch.squeeze(cur_pos))
        # next_pos = prediction
        '''
        print("next_pos shape")
        print(next_pos.shape)
        '''
        trajectory.append(cur_pos)
        return cur_pos, next_pos, trajectory

    '''
    _, _, _, output = tf.while_loop(
        cond=lambda step, last, cur, traj: tf.less(step, num_steps),
        body=step_fn,
        loop_vars=(0, initial_state['prev|world_pos'], initial_state['world_pos'],
                   tf.TensorArray(tf.float32, num_steps)),
        parallel_iterations=1)
    '''
    prev_pos = torch.squeeze(initial_state['prev|world_pos'], 0)
    cur_pos = torch.squeeze(initial_state['world_pos'], 0)
    trajectory = []
    for step in range(num_steps):
        prev_pos, cur_pos, trajectory = step_fn(prev_pos, cur_pos, trajectory)
    return torch.stack(trajectory)


def evaluate(model, trajectory):
    """Performs model rollouts and create stats."""
    '''
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(name)
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(param.data)
    quit()
    '''
    initial_state = {k: torch.squeeze(v, 0)[0] for k, v in trajectory.items()}
    num_steps = trajectory['cells'].shape[0]
    prediction = _rollout(model, initial_state, num_steps)

    # error = tf.reduce_mean((prediction - trajectory['world_pos'])**2, axis=-1)
    # scalars = {'mse_%d_steps' % horizon: tf.reduce_mean(error[1:horizon+1])
    #            for horizon in [1, 10, 20, 50, 100, 200]}

    scalars = None
    traj_ops = {
        'faces': trajectory['cells'],
        'mesh_pos': trajectory['mesh_pos'],
        'gt_pos': trajectory['world_pos'],
        'pred_pos': prediction
    }
    # for step in prediction['world']
    return scalars, traj_ops
