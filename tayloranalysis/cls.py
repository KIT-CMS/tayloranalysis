import matplotlib.pyplot as plt
import numpy as np
import torch

from datetime import datetime
from torch import nn
from torch.autograd.functional import jacobian
from torch.utils.data import TensorDataset, DataLoader
from torch.autograd import grad


class TaylorAnalysis(nn.Module):
    """
    Class to wrap nn.Module for taylorcoefficient analysis.
    """
    def __init__(self, model):
        """Class init to wrap nn.Module

        Args:
            model (nn.Module): Pytorch model with scalar output to wrap.
        """
        super().__init__()
        self.model = model
        self.checkpoints = {}

    def forward(self, x):
        """Overwrite the model's forward function.

        Args:
            x (torch.tensor): input tensor of shape (batch, features)

        Returns:
            torch.tensor: model output of shape (batch)
        """
        return self.model(x)

    def _mean(self, data):
        """Compute abs and mean of taylorcoefficients.

        Args:
            data (torch.tensor): tensor with taylorcoefficients of shape (batch, features)

        Returns:
            numpy.array: Array means of taylorcoefficients.
        """
        data = torch.abs(data)
        data = torch.mean(data, dim=0)
        return data.cpu().detach().numpy()
    
    def _first_order(self, x_data):
        """Compute first order taylorcoefficients.

        Args:
            x_data (torch.tensor): X data of shape (batch, features).

        Returns:
            torch.tensor: First order taylorcoefficients (batch, features).
        """
        x_data.requires_grad = True
        self.model.zero_grad()
        x_data.grad = None
        pred = self.model(x_data)
        pred = pred.sum()
        # first order grads
        gradients = grad(pred, x_data) 
        return self._mean(gradients[0])

    def _second_order(self, x_data, ind_i):
        """Compute second order taylorcoefficients. The model is first derivated according to the ind_i-th feature and second to all others. 

        Args:
            x_data (torch.tensor): X data (batch, features).
            ind_i (int): Feature for the first derivative.

        Returns:
            torch.tensor: Second order derivatives according to ind_i and all other input variables (batch, feature). 
        """
        x_data.requires_grad = True
        self.model.zero_grad()
        x_data.grad = None
        pred = self.model(x_data)
        pred = pred.sum()
        # first order gradients
        gradients = grad(pred, x_data, create_graph=True) 
        gradients = gradients[0].sum(dim=0)
        # second order gradients
        gradients = grad(gradients[ind_i], x_data) 
        return self._mean(gradients[0])

    def _third_order(self, x_data, ind_i, ind_j):
        """Compute third order taylorcoefficients. The model is derivated to the ind_i-th feature, 
            the ind_j-th feature and third to all other features.

        Args:
            x_data (torch.tensor): X data (batch, features).
            ind_i (int): Feature for the first derivative.
            ind_j (int): Feature for the second derivative.

        Returns:
            torch.tensor: Third order derivatives according to ind_i, ind_j and all other input features (batch, feature). 
        """
        x_data.requires_grad = True
        self.model.zero_grad()
        x_data.grad = None
        pred = self.model(x_data)
        pred = pred.sum()
        # first order gradients
        gradients = grad(pred, x_data, create_graph=True)
        gradients = gradients[0].sum(dim=0)
        # second order gradients
        gradients = grad(gradients[ind_i], x_data, create_graph=True) 
        gradients = gradients[0].sum(dim=0)
        # third order gradients
        gradients = grad(gradients[ind_j], x_data) 
        return self._mean(gradients[0])

    def plot_tc(self, data, names, path='', order=2, split=False):
        """Plot taylorcoefficients for current weights of the model.

        Args:
            data (torch.tensor): X data of shape (batch, features).
            names (list): List of feature names. Should have the same order as in the input tensor
            path (str): /path/to/save/plot.pdf
            order (int, optional): Order up to which the taylorcoefficients should be plotted. Defaults to 2.
            split (bool, optional): Produce one plot for each derivation order.
        """
        # first order
        derivatives = self._first_order(data)
        for i in range(len(names)):
            plt.plot('$<t_{{{}}}>$'.format(names[i]), derivatives[i], 
                    '+', color='black', markersize=10)
            if split:
                plt.ylabel('$<t_i>$', loc='top', fontsize=13)
                plt.xticks(rotation=45)
                plt.tick_params(axis='y', which='both', right=True, direction='in')
                plt.tick_params(axis='x', which='both', top=True, direction='in')
                plt.savefig(path+'coefficients_first_order.pdf', bbox_inches = "tight")
                plt.clf()

        # second order
        if order >=2:
            for i in range(len(names)):
                derivatives = self._second_order(data, i)
                for j in range(len(names)):
                    if i<=j: # ignore diagonal elements
                        plt.plot('$<t_{{{},{}}}$>'.format(names[i], names[j]), 
                                derivatives[j], '+', color='black', markersize=10)
                        if split:
                            plt.ylabel('$<t_i>$', loc='top', fontsize=13)
                            plt.xticks(rotation=45)
                            plt.tick_params(axis='y', which='both', right=True, direction='in')
                            plt.tick_params(axis='x', which='both', top=True, direction='in')
                            plt.savefig(path+'coefficients_second_order.pdf', bbox_inches = "tight")
                            plt.clf()
        # third order
        if order >=3:
            for i in range(len(names)):
                for j in range(len(names)):
                    derivatives = self._third_order(data, i, j)
                    for k in range(len(names)):
                        if i<=j<=k:  # ignore diagonal elements
                            plt.plot('$<t_{{{},{},{}}}>$'.format(names[i], names[j], names[k]), 
                                    derivatives[k], '+', color='black', markersize=10)
                            if split:
                                plt.ylabel('$<t_i>$', loc='top', fontsize=13)
                                plt.xticks(rotation=45)
                                plt.tick_params(axis='y', which='both', right=True, direction='in')
                                plt.tick_params(axis='x', which='both', top=True, direction='in')
                                plt.savefig(path+'coefficients_third_order.pdf', bbox_inches = "tight")
                                plt.clf()
                            
        if not split:
            plt.ylabel('$<t_i>$', loc='top', fontsize=13)
            plt.xticks(rotation=45)
            plt.tick_params(axis='y', which='both', right=True, direction='in')
            plt.tick_params(axis='x', which='both', top=True, direction='in')
            plt.savefig(path+'coefficients.pdf', bbox_inches = "tight")
            plt.clf()

    def tc_checkpoint(self, x_data, names, order=2):
        """Compute and save taylorcoefficients to plot them later.

        Args:
            x_data (torch.tensor): X data (batch, features)
            names (list): List of feature names. Should have the same order as in the input tensor
            order (int, optional): Order up to which the taylorcoefficients should be plotted. Defaults to 2.
        """
        # first order
        if order >= 1:
            coefs= self._first_order(x_data)
            for i, name in enumerate(names):
                name = '$<t_{{{}}}>$'.format(name)
                if name not in self.checkpoints.keys(): 
                    self.checkpoints[name] = []
                self.checkpoints[name].append(coefs[i])

        # second order
        if order >= 2:
            for i, name_i in enumerate(names):
                coefs= self._second_order(x_data, i)
                for j, name_j in enumerate(names):
                    if i<=j: # ignore diagonal elements
                        name = '$<t_{{{},{}}}>$'.format(name_i, name_j)
                        if name not in self.checkpoints.keys(): 
                            self.checkpoints[name] = []
                        self.checkpoints[name].append(coefs[j])

        # third order
        if order >= 3:
            for i, name_i in enumerate(names):
                for j, name_j in enumerate(names):
                    coefs= self._third_order(x_data, i, j)
                    for k, name_k in enumerate(names):
                        if i<=j<=k:  # ignore diagonal elements
                            name = '$<t_{{{},{},{}}}>$'.format(name_i, name_j, name_k)
                            if name not in self.checkpoints.keys(): 
                                self.checkpoints[name] = []
                            self.checkpoints[name].append(coefs[k])
                        
    def plt_checkpoints(self, path=''):
        """Plot saved checkpoints.

        Args:
            path (str): /path/to/save/plot.pdf
        """
        # color setup
        NUM_COLORS = len(self.checkpoints)
        cm = plt.get_cmap('gist_rainbow')
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_prop_cycle('color', [cm(1.*i/NUM_COLORS) for i in range(NUM_COLORS)])
        
        for name, coef in self.checkpoints.items():
            ax.plot(coef, label=name)
            
        plt.legend(loc='upper left', bbox_to_anchor=(1.04, 1))
        plt.xlabel('Epoch', loc='right', fontsize=13)
        plt.ylabel('$<t_i>$', loc='top', fontsize=13)
        plt.tick_params(axis='y', which='both', right=True, direction='in')
        plt.tick_params(axis='x', which='both', top=True, direction='in')
        plt.savefig(path+'tc_training.pdf', bbox_inches = "tight")
        plt.clf()
        
    def clear_checkpoints(self):
        """clear saved checkpoints
        """
        self.checkpoints = {}


