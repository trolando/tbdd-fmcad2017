#!/usr/bin/env python
from __future__ import print_function
from contextlib import contextmanager
import os
import sys
import re
from itertools import chain, ifilter
from tabulate import tabulate
from numpy import nanmin

# import framework
from expfw import Experiment, ExperimentEngine, online_variance, fixnan


colors = True
if colors:
    from termcolor import colored


class ExpLTSmin(Experiment):
    def parse_log(self, contents):
        res = {}
        s = re.compile(r'reachability took ([\d\.,]+)').findall(contents)
        if len(s) != 1:
            return None
        res['time'] = float(s[0])
        s = re.compile(r'state space has ([\d\.,]+) states, ([\d\.,]+) nodes').findall(contents)
        if len(s) != 1:
            return None
        res['states'] = int(s[0][0])
        res['nodes'] = int(s[0][1])
        s = re.compile(r'group_next: ([\d\.,]+) nodes total').findall(contents)
        if len(s) != 1:
            return None
        res['nextnodes'] = int(s[0])
        return res

    def get_text(self, res):
        return "{} seconds".format(res['time'])


class ExpBDD(ExpLTSmin):
    def __init__(self, name, workers, model):
        self.group = name
        self.name = "{}-bdd-{}".format(name, workers)
        self.call = ["./dve2lts-sym", "--when", "-rf", "--lace-workers={}".format(workers), "--vset=sylvan", model]


class ExpTBDD(ExpLTSmin):
    def __init__(self, name, workers, model):
        self.group = name
        self.name = "{}-tbdd-{}".format(name, workers)
        self.call = ["./dve2lts-sym", "--when", "-rf", "--lace-workers={}".format(workers), "--vset=tbdd", model]


class ExpLDD(ExpLTSmin):
    def __init__(self, name, workers, model):
        self.group = name
        self.name = "{}-ldd-{}".format(name, workers)
        self.call = ["./dve2lts-sym", "--when", "-rf", "--lace-workers={}".format(workers), "--vset=lddmc", model]


class ExpPnmlBDD(ExpLTSmin):
    def __init__(self, name, workers, model):
        self.group = name
        self.name = "{}-bdd-{}".format(name, workers)
        self.call = ["./pnml2lts-sym", "--when", "-rf", "--lace-workers={}".format(workers), "--vset=sylvan", model]


class ExpPnmlTBDD(ExpLTSmin):
    def __init__(self, name, workers, model):
        self.group = name
        self.name = "{}-tbdd-{}".format(name, workers)
        self.call = ["./pnml2lts-sym", "--when", "-rf", "--lace-workers={}".format(workers), "--vset=tbdd", model]


class ExpPnmlLDD(ExpLTSmin):
    def __init__(self, name, workers, model):
        self.group = name
        self.name = "{}-ldd-{}".format(name, workers)
        self.call = ["./pnml2lts-sym", "--when", "-rf", "--lace-workers={}".format(workers), "--vset=lddmc", model]


def float_str(f):
    if str(f) == 'nan':
        return '--'
    else:
        return str(int(f))


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


class DveExperiments(object):
    def __init__(self, blocks_first=True):
        # initialize self.models
        with cd("dve"):
            files = list(filter(os.path.isfile, os.listdir(os.curdir)))
        files = [f[:-len(".dve2C")] for f in filter(lambda f: f.endswith(".dve2C"), files)]
        self.models = tuple([x, "dve/{}.dve2C".format(x)] for x in files)

        # add for each model
        self.ldd1 = {}
        self.ldd48 = {}
        self.bdd1 = {}
        self.bdd48 = {}
        self.tbdd1 = {}
        self.tbdd48 = {}
        for name, filename in self.models:
            self.ldd1[name] = ExpLDD(name, 1, filename)
            self.bdd1[name] = ExpBDD(name, 1, filename)
            self.tbdd1[name] = ExpTBDD(name, 1, filename)
            self.ldd48[name] = ExpLDD(name, 48, filename)
            self.bdd48[name] = ExpBDD(name, 48, filename)
            self.tbdd48[name] = ExpTBDD(name, 48, filename)

    def all_experiments(self):
        dicts = ["ldd1", "ldd48", "bdd1", "bdd48", "tbdd1", "tbdd48"]
        return chain(*(getattr(self, x).values() for x in dicts))

    def grouped_experiments(self):
        dicts = ["ldd1", "ldd48", "bdd1", "bdd48", "tbdd1", "tbdd48"]
        dicts = tuple(getattr(self, x) for x in dicts)
        for k in set(chain(*(x.keys() for x in dicts))):
            yield [x[k] for x in ifilter(lambda x: k in x, dicts)]

    def __iter__(self):
        return self.grouped_experiments()

    def analyse_experiment(self, name, results):
        r = {}
        # time, states, nodes, nextnodes
        # compute (count,average) for all times
        dicts = ["ldd1", "ldd48", "bdd1", "bdd48", "tbdd1", "tbdd48"]
        for d in dicts:
            results_for_d = [v for exp, v in results if exp == getattr(self, d)[name]]
            r['n_'+d], r['t_'+d] = online_variance([v['time'] for v in results_for_d])[0:2]
            r['nodes_'+d] = online_variance([v['nodes'] for v in results_for_d])[1]
            r['nextnodes_'+d] = online_variance([v['nextnodes'] for v in results_for_d])[1]
            r['states_'+d] = online_variance([v['states'] for v in results_for_d])[1]
        return r

    def analyse(self, results):
        data = {}
        for name, fn in self.models:
            data[name] = self.analyse_experiment(name, results)
        self.data = data
        return data

    def report(self, res=None):
        if res is None:
            res = self.data

        # Report number of completed experiments
        table = []
        for name in sorted(res.keys()):
            r = res[name]
            table.append([name,
                          "{}".format(r['n_bdd1']),
                          "{}".format(r['n_bdd48']),
                          "{}".format(r['n_tbdd1']),
                          "{}".format(r['n_tbdd48']),
                          "{}".format(r['n_ldd1']),
                          "{}".format(r['n_ldd48']),
                          ])
        table = fixnan(table)
        headers = ["Model      ", "#bdd1", "#bdd48", "#tbdd1", "#tbdd48", "#ldd1", "#ldd48"]
        print(tabulate(table, headers))

        print()

        # Remove experiments that are not done
        exp_sum = lambda r: r['n_bdd1'] + r['n_bdd48'] + r['n_tbdd1'] + r['n_tbdd48'] + r['n_ldd1'] + r['n_ldd48']
        names = sorted(filter(lambda f: exp_sum(res[f]) > 0, res.keys()))

        # Report times
        table = []
        for name in names:
            r = res[name]
            t_bdd1 = "{:<6.2f}".format(r['t_bdd1'])
            t_tbdd1 = "{:<6.2f}".format(r['t_tbdd1'])
            t_ldd1 = "{:<6.2f}".format(r['t_ldd1'])
            t_bdd48 = "{:<6.2f}".format(r['t_bdd48'])
            t_tbdd48 = "{:<6.2f}".format(r['t_tbdd48'])
            t_ldd48 = "{:<6.2f}".format(r['t_ldd48'])
            if colors:
                lowest1 = nanmin([r['t_bdd1'], r['t_tbdd1'], r['t_ldd1']])
                lowest48 = nanmin([r['t_bdd48'], r['t_tbdd48'], r['t_ldd48']])
                if r['t_bdd1'] == lowest1: t_bdd1 = colored(t_bdd1, 'green', attrs=['bold'])
                if r['t_tbdd1'] == lowest1: t_tbdd1 = colored(t_tbdd1, 'green', attrs=['bold'])
                if r['t_ldd1'] == lowest1: t_ldd1 = colored(t_ldd1, 'green', attrs=['bold'])
                if r['t_bdd48'] == lowest48: t_bdd48 = colored(t_bdd48, 'green', attrs=['bold'])
                if r['t_tbdd48'] == lowest48: t_tbdd48 = colored(t_tbdd48, 'green', attrs=['bold'])
                if r['t_ldd48'] == lowest48: t_ldd48 = colored(t_ldd48, 'green', attrs=['bold'])
            if r['t_bdd48'] > 0:
                s_bdd = r['t_bdd1']/r['t_bdd48']
            else:
                s_bdd = float('nan')
            if r['t_tbdd48'] > 0:
                s_tbdd = r['t_tbdd1']/r['t_tbdd48']
            else:
                s_tbdd = float('nan')
            if r['t_ldd48'] > 0:
                s_ldd = r['t_ldd1']/r['t_ldd48']
            else:
                s_ldd = float('nan')
            table.append([name,
                          t_bdd1, t_tbdd1, t_ldd1, t_bdd48, t_tbdd48, t_ldd48,
                          "{:<6.2f}".format((s_bdd)),
                          "{:<6.2f}".format((s_tbdd)),
                          "{:<6.2f}".format((s_ldd)),
                          ])

        table = fixnan(table)
        headers = ["Model      ", "T_bdd1", "T_bdd48", "Sbdd", "T_tbdd1", "T_tbdd48", "Stbdd", "T_ldd1", "T_ldd48", "Sldd"]
        print(tabulate(table, headers))

        print()

        # Report sizes
        table = []
        for name in names:
            r = res[name]
            nodes_bdd1 = "{}".format(r['nodes_bdd1'])
            nodes_tbdd1 = "{}".format(r['nodes_tbdd1'])
            nodes_ldd1 = "{}".format(r['nodes_ldd1'])
            nodes_bdd48 = "{}".format(r['nodes_bdd48'])
            nodes_tbdd48 = "{}".format(r['nodes_tbdd48'])
            nodes_ldd48 = "{}".format(r['nodes_ldd48'])
            if colors:
                lowest1 = nanmin([r['nodes_bdd1'], r['nodes_tbdd1'], r['nodes_ldd1']])
                lowest48 = nanmin([r['nodes_bdd48'], r['nodes_tbdd48'], r['nodes_ldd48']])
                if r['nodes_bdd1'] == lowest1: nodes_bdd1 = colored(nodes_bdd1, 'green', attrs=['bold'])
                if r['nodes_tbdd1'] == lowest1: nodes_tbdd1 = colored(nodes_tbdd1, 'green', attrs=['bold'])
                if r['nodes_ldd1'] == lowest1: nodes_ldd1 = colored(nodes_ldd1, 'green', attrs=['bold'])
                if r['nodes_bdd48'] == lowest48: nodes_bdd48 = colored(nodes_bdd48, 'green', attrs=['bold'])
                if r['nodes_tbdd48'] == lowest48: nodes_tbdd48 = colored(nodes_tbdd48, 'green', attrs=['bold'])
                if r['nodes_ldd48'] == lowest48: nodes_ldd48 = colored(nodes_ldd48, 'green', attrs=['bold'])
 
            table.append([name, nodes_bdd1, nodes_tbdd1, nodes_ldd1])

        table = fixnan(table)
        headers = ["Model      ", "N_bdd", "N_tbdd", "N_ldd"]
        print(tabulate(table, headers))


class PnmlExperiments(DveExperiments):
    def __init__(self, blocks_first=True):
        # initialize self.models
        with cd("pnml"):
            files = list(filter(os.path.isfile, os.listdir(os.curdir)))
        files = [f[:-len(".pnml")] for f in filter(lambda f: f.endswith(".pnml"), files)]
        self.models = tuple([x, "pnml/{}.pnml".format(x)] for x in files)

        # add for each model
        self.ldd1 = {}
        self.ldd48 = {}
        self.bdd1 = {}
        self.bdd48 = {}
        self.tbdd1 = {}
        self.tbdd48 = {}
        for name, filename in self.models:
            self.ldd1[name] = ExpPnmlLDD(name, 1, filename)
            self.bdd1[name] = ExpPnmlBDD(name, 1, filename)
            self.tbdd1[name] = ExpPnmlTBDD(name, 1, filename)
            self.ldd48[name] = ExpPnmlLDD(name, 48, filename)
            self.bdd48[name] = ExpPnmlBDD(name, 48, filename)
            self.tbdd48[name] = ExpPnmlTBDD(name, 48, filename)

 
# the experiments
dve = DveExperiments()
pnml = PnmlExperiments()

# make engine
sr = ExperimentEngine(outdir='logs', timeout=1200)
sr += dve
# sr += pnml

if __name__ == "__main__":
    # select engine
    engine = sr

    if len(sys.argv) > 1:
        if sys.argv[1] == 'run':
            sr.run_experiments()
        elif sys.argv[1] == 'report':
            sr.get_results()
            # flatten results
            results = [res for sublist in sr.results for res in sublist]
            dve.analyse(results)
            pnml.analyse(results)
            dve.report()
            #pnml.report()

            # with open('results_ctmc.tex', 'w') as f:
            #    ctmc.report_latex(f)
