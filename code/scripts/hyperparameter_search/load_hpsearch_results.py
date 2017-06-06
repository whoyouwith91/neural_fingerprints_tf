import argparse, os, time
import numpy as np


def parse_input_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_path", help="Path to directory containing a set of subdirectories, each containing the "
                                             "results of a certain trained configuration. Corresponds to "
                                             "${NF_HOMEDIR}/output/hyperparameter_search/${DATASET_NAME} in the "
                                             "hpsearch_${DATASET_NAME}.sh scripts.", type=str)
    parser.add_argument("--results_fname", help="Results filename. Defaults to main_loss_results.npy.", type=str,
                        default="main_loss_results.npy")

    return parser.parse_args()


def retrieve_configuration_files(basepath, results_fname):
    print 'Searching for training output in directory %s...' % basepath
    config_list = [subdir for subdir in os.listdir(basepath) if os.path.isdir(os.path.join(basepath, subdir))]
    config_list_success = [subdir for subdir in config_list if
                           os.path.isfile(os.path.join(basepath, subdir, results_fname))]
    n_config = len(config_list_success)
    print '%d subdirectories found, %d with training results.\n' % (len(config_list), n_config)

    return config_list_success, n_config


def load_results(basepath, results_fname, config_list):
    print 'Loading results...'
    tic = time.time()
    loss_val, loss_tst = [], []
    for subdir in config_list:
        out_val, out_tst = np.load(os.path.join(basepath, subdir, results_fname))
        loss_val.append(out_val)
        loss_tst.append(out_tst)

    # Convert lists to NumPy arrays
    loss_val, loss_tst = np.stack(loss_val), np.stack(loss_tst)

    toc = time.time()
    print 'Loaded results for %d configurations in %0.03f seconds.\n' % (n_config, toc - tic)

    return loss_val, loss_tst


def early_stopping(loss_val, loss_tst):
    # Number of configurations
    n_config = loss_val.shape[0]
    # Sanity-check
    assert loss_tst.shape[0] == n_config

    # Find epoch with smallest validation loss for each configuration
    idx_es = np.argmin(loss_val, axis=1)
    # Corresponding validation and test set loss
    es_loss_val = loss_val[np.arange(n_config), idx_es]
    es_loss_tst = loss_tst[np.arange(n_config), idx_es]

    return es_loss_val, es_loss_tst, idx_es


def best_config(es_loss_val, es_loss_tst, idx_es, config_list):
    # Find best performing configuration according to validation loss
    best_config_idx = np.argmin(es_loss_val)

    # Filename of best performing configuration, as well as best performing epoch (according to validation loss)
    best_config = config_list[best_config_idx]
    best_epoch = idx_es[best_config_idx]

    # Corresponding validation and test loss
    best_val_loss = es_loss_val[best_config_idx]
    best_tst_loss = es_loss_tst[best_config_idx]

    return best_val_loss, best_tst_loss, best_config, best_epoch

# ---------------------------------------------------- SCRIPT ----------------------------------------------------------

# Parse input arguments first
args = parse_input_arguments()

# Make sure that args.results_path directory exists
if not os.path.isdir(args.results_path):
    raise ValueError("Directory %s does not exist." % args.results_path)

# Retrieve list of configurations in directory args.results_path that have available results, as generated by the
# Trainer class
config_list, n_config = retrieve_configuration_files(args.results_path, args.results_fname)

# Load validation and test loss per config, per epoch
loss_val, loss_tst = load_results(args.results_path, args.results_fname, config_list)

# Apply early-stopping, according to validation loss
es_loss_val, es_loss_tst, idx_es = early_stopping(loss_val, loss_tst)

# Find best performing configuration, according to validation loss
best_val_loss, best_tst_loss, best_config, best_epoch = best_config(es_loss_val, es_loss_tst, idx_es, config_list)
print 'Best validation set loss: %0.03f. Achieved for configuration %s at epoch %d.' \
      % (best_val_loss, best_config, best_epoch)
print 'Corresponding test set loss: %0.03f.\n' % best_tst_loss