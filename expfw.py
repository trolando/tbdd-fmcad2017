#!/usr/bin/env python
from __future__ import print_function
import os
import sys
from subprocess32 import call, TimeoutExpired
import time
import random
import itertools


class Experiment(object):
    NOTDONE = 0
    DONE = 1
    TIMEOUT = 2

    def __init__(self, name, call, group=None):
        self.name = name
        self.call = call
        self.group = group

    def parse_log(self, contents):
        """Parse the log file.

        Return None if not good, or a dict with the results otherwise.
        """
        return None

    def get_text(self, res):
        """Given the result of parse_log, return a str representing the main result.
        """
        return ""

    def get_status(self, filename):
        """Obtain the status of the experiment.

        Return a pair:
        (Experiment.DONE, res)
        (Experiment.TIMEOUT, time)
        (Experiment.NOTDONE, None)
        """
        if (os.path.isfile(filename)):
            with open(filename, 'r') as handle:
                res = self.parse_log(handle.read())
                if res is not None:
                    return Experiment.DONE, res

        timeout_filename = "{}.timeout".format(filename)
        if (os.path.isfile(timeout_filename)):
            with open(timeout_filename, 'r') as handle:
                return Experiment.TIMEOUT, int(handle.read())

        return Experiment.NOTDONE, None

    def run_experiment(self, timeout, filename):
        # remove output and timeout files
        if os.path.isfile(filename):
            os.unlink(filename)
        timeout_filename = "{}.timeout".format(filename)
        if os.path.isfile(timeout_filename):
            os.unlink(timeout_filename)

        # report that we are running the experiment
        print("Performing {}... ".format(self.name), end='')
        sys.stdout.flush()

        try:
            with open(filename, 'w+') as out:
                call(self.call, stdout=out, stderr=out, timeout=timeout)
        except KeyboardInterrupt:
            # if CTRL-C was hit, move the file
            os.rename(filename, "{}.interrupted".format(filename))
            print("interrupted.")
            sys.exit()
        except OSError:
            # OS error (probably missing executable)
            print("OS failure. (missing executable?)")
            sys.exit()
        except TimeoutExpired:
            # timeout hit, write current timeout value to timeout file
            with open(timeout_filename, 'w') as handle:
                handle.write(str(timeout))
            print("timeout.")
            return Experiment.TIMEOUT, timeout
        else:
            # experiment finished, either report done or not done...
            status, value = self.get_status(filename)
            if status == Experiment.DONE:
                print("done; {}.".format(self.get_text(value)))
            else:
                print("not done.")
            return status, value


class ExperimentEngine(object):
    def __init__(self, **kwargs):
        """Initialize a set of experiments.

        Parameters:
        - logdir (default "logs")
        - timeout (default 1200 seconds)
        """
        self.experiments = []
        if 'logdir' in kwargs:
            self.logdir = kwargs['logdir']
        else:
            self.logdir = 'logs'
        if 'timeout' in kwargs:
            self.timeout = int(kwargs['timeout'])
        else:
            self.timeout = 1200

    def get_results(self):
        """Get all results.
        """

        self.results = []
        self.timeouts = []
        self.notdone = []
        for i in itertools.count():
            results = []
            timeouts = []
            notdone = []
            for e in self.experiments:
                status, value = e.get_status("{}/{}-{}".format(self.logdir, e.name, i))
                if status == Experiment.DONE:
                    results.append((e, value))
                elif status == Experiment.TIMEOUT:
                    timeouts.append((e, value))
                else:
                    notdone.append(e)
            if len(results) == 0:
                return
            self.results.append(results)
            self.timeouts.append(timeouts)
            self.notdone.append(notdone)

    def run_experiments(self):
        """Run experiments indefinitely.
        """
        # create directory
        if not os.path.exists(self.logdir):
            os.makedirs(self.logdir)

        # obtain results so far
        self.get_results()

        # now move low timeouts to notdone
        for i in xrange(0, len(self.results)):
            self.notdone[i] += [x[0] for x in self.timeouts[i] if x[1] < self.timeout]
            self.timeouts[i] = [x for x in self.timeouts[i] if x[1] >= self.timeout]

        # report current status
        n_iterations = len(self.results)
        n_successful = sum([len(x) for x in self.results])
        n_timeout = sum([len(x) for x in self.timeouts])
        n_notdone = n_iterations * len(self.experiments) - n_successful - n_timeout
        print("In {} iterations, {} successful, {} timeouts, {} not done.".format(
            n_iterations, n_successful, n_timeout, n_notdone))

        for i in itertools.count():
            if i < n_iterations:
                todo = self.notdone[i]
                self.notdone[i] = []
            else:
                todo = self.experiments
                self.results.append([])
                self.timeouts.append([])
                self.notdone.append([])
            random.shuffle(todo)
            while len(todo):
                # get next experiment (random)
                e = random.choice(todo)
                # get all experiments with this group
                if getattr(e, 'group', None) is not None:
                    exps = [x for x in todo if x.group == e.group]
                    todo = [x for x in todo if x.group != e.group]
                else:
                    exps = [e]
                    todo.remove(e)
                for j, e in enumerate(exps):
                    # print header
                    print("{} iteration {} ({}/{}): ".format(time.strftime('%X'), i, len(self.experiments)-len(todo)-len(exps)+j+1, len(self.experiments)), end='')
                    # run experiment
                    filename = "{}/{}-{}".format(self.logdir, e.name, i)
                    status, value = e.run_experiment(self.timeout, filename)
                    # store result
                    if status == Experiment.DONE:
                        self.results[i] += [(e, value)]
                    elif status == Experiment.TIMEOUT:
                        self.timeouts[i] += [(e, value)]
                    else:
                        self.notdone[i] += [e]
                    # sleep 2 seconds to allow OS to swap stuff in or out
                    time.sleep(2)
            print("Iteration {} done.".format(i))

    def __iadd__(self, other):
        if isinstance(other, Experiment):
            self.experiments.append(other)
            return self
        elif isinstance(other, ExperimentEngine):
            self.experiments.extend(other)
            return self
        elif hasattr(other, '__iter__'):
            for item in other:
                self += item
            return self
        else:
            return NotImplemented


def online_variance(data):
    n = 0
    mean = 0
    M2 = 0

    for x in data:
        n = n + 1
        delta = x - mean
        mean = mean + delta / n
        M2 = M2 + delta * (x - mean)

    if n < 1:
        return n, float('nan'), float('nan')
    if n < 2:
        return n, mean, float('nan')

    variance = M2 / (n - 1)
    return n, mean, variance


def fixnan(table):
    return [['--' if s.strip() == 'nan' else s for s in row] for row in table]
