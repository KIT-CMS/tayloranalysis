import pickle
import time

import torch
from tayloranalysis import TaylorAnalysis
from torch import nn

# load data

data = pickle.load(open("../../data/multivariate/multiclass_data.pickle", "rb"), encoding="latin-1")
x_train = torch.tensor(data["x_train"], dtype=torch.float)
y_train = torch.tensor(data["y_train"], dtype=torch.long).t()

# initialize normal pytorch MLP model


class Mlp(nn.Module):
    def __init__(self, input_neurons, hidden_neurons, output_neurons, hiddenlayers):

        nn.Module.__init__(self)

        # mlp layers
        self.mlplayers = nn.ModuleList([nn.Linear(input_neurons, hidden_neurons)])
        self.mlplayers.extend([nn.Linear(hidden_neurons, hidden_neurons) for i in range(hiddenlayers + 1)])
        self.mlplayers.append(nn.Linear(hidden_neurons, output_neurons))

    def forward(self, x):
        # input shape: (batch, features)
        for mlplayer in self.mlplayers[:-1]:
            x = mlplayer(x)
            x = torch.tanh(x)

        # new x: (batch, 1)
        x = self.mlplayers[-1](x)
        x = x.squeeze(-1)  # new x: (batch)
        x = torch.sigmoid(x)
        return x


model = Mlp(2, 100, 3, 2)

# wrap model with TaylorAnalysis

model = TaylorAnalysis(model)

# setup for normal training

optim = torch.optim.Adam(model.parameters(), lr=0.001)
crit = nn.CrossEntropyLoss()

device = torch.device(1)  # choose your device you want to train on
x_train = x_train.to(device)
y_train = y_train.to(device)
model.to(device)

x_train.requires_grad = True

# setup the tc checkpoints

model.setup_tc_checkpoints(
    number_of_variables_in_data=2,
    considered_variables_idx=[0, 1],
    variable_names=["x_1", "x_2"],
    derivation_order=3,
    eval_nodes=[0, 1, (0, 1), "all"],  # single int or 'all' is also possible
    eval_only_max_node=False,
)

start = time.time()
for epoch in range(150):
    optim.zero_grad()
    pred = model(x_train)
    loss = crit(pred, y_train)
    loss.backward()
    optim.step()
    print("Epoch {}: Loss: {:.3f}".format(epoch + 1, loss))

    # save current taylorcoefficients
    model.tc_checkpoint(x_train, epoch=epoch)

end = time.time()
print("Time needed:", round(end - start, 2))

# load test data

x_test = torch.tensor(data["x_test"], dtype=torch.float).to(device)

# plot taylorcoefficients after training

# calculate tc explicitly
model.calculate_tc(
    x_data=x_test,
    considered_variables_idx=[0, 1],
    derivation_order=3,
    eval_nodes=[0, 1, (0, 1), 2, "all"],  # single int or 'all' is also possible
    eval_only_max_node=False,
)

# or implicitly by providing necessary quantities to the plotting function
model.plot_taylor_coefficients(
    # kwargs (!) passed to calculate_tc if 'model.calculate_tc' not called explicetly previously
    x_data=x_test,
    considered_variables_idx=[0, 1],
    derivation_order=3,
    eval_nodes=[0, 1, (0, 1), 2, "all"],  # single int or 'all' is also possible
    eval_only_max_node=False,
    # plotting keargs
    variable_names=["x_1", "x_2"],
    sorted=True,
    number_of_tc_per_plot=20,
    path=["./coefficients.pdf", "./coefficients.png"],
)

# plot saved checkpoints
model.plot_checkpoints(
    variable_names=["x_1", "x_2"],
    path=["./tc_training.pdf", "./tc_training.png"],
)
# model.save_tc_points(path="./tc_checkpoints.csv")
