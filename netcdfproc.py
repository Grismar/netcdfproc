# http://unidata.github.io/netcdf4-python/

from netCDF4 import Dataset
import json
import numpy
import os
import sys
import argparse


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.integer):
            return int(obj)
        elif isinstance(obj, numpy.floating):
            return float(obj)
        elif isinstance(obj, numpy.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)


def process_netcdf_file(filename, d1_to_csv, d2_to_csv, fmt):
    def process_netcdf(dataset, basename):
        assert (dataset.data_model == 'NETCDF4'), "can only process netCDF4"

        def process_variable(variable, dimensions, data):
            variable_result = {}
            for name in variable.ncattrs():
                variable_result[name] = getattr(variable, name)

            assert (len(variable.dimensions) < 3), "unexpected number of dimensions (>2)"
            if len(variable.dimensions) == 0:
                variable_result['__size'] = [1]
            else:
                variable_result['__size'] = []
                for d in variable.dimensions:
                    variable_result['__size'].append(dimensions[d].size)

            if (len(variable.shape) == 1 and d1_to_csv) or (len(variable.shape) == 2 and d2_to_csv):
                csv_name = basename+'.'+variable.name+'.csv'
                if fmt == '':
                    numpy.savetxt(csv_name, variable, delimiter=',')
                else:
                    numpy.savetxt(csv_name, variable, fmt=fmt, delimiter=',')
                data[variable.name] = csv_name
            else:
                data[variable.name] = numpy.asarray(variable)

            return variable_result

        def process_group(group):
            result = {
                'subgroups': {},
                'global_attributes': {},
                'variables': {},
                'data': {}
            }

            for name, subgroup in group.groups.items():
                result['subgroups'][name] = process_group(subgroup)

            for name in group.ncattrs():
                result['global_attributes'][name] = getattr(group, name)

            for name in group.variables:
                result['variables'][name] = process_variable(group.variables[name], group.dimensions, result['data'])

            return result

        root_group = process_group(dataset)
        root_group['global_attributes']['__source'] = basename
        return root_group

    return process_netcdf(Dataset(filename, "r+", format="NETCDF4"), os.path.basename(filename))


argparser = argparse.ArgumentParser(description='Process netCDF4 into JSON/csv.')
argparser.add_argument('input', nargs=1,
                       help='netCDF4 input file.')
argparser.add_argument('-c', '--csv', action='store_true',
                       help='Output anything in a 1d or 2d array as a .csv instead of a JSON array.')
argparser.add_argument('-c2', '--csv_2d', action='store_true',
                       help='Output anything in a 2d array as a .csv instead of a JSON array.')
argparser.add_argument('-o', '--out_file',
                       help='Instead of dumping to standard out, write JSON output to a file.')
argparser.add_argument('-f', '--format', default='',
                       help='Formatting string for csv output (no effect if no csv is written).')
args = argparser.parse_args(sys.argv[1:])


try:
    assert (len(args.input) == 1), "No input file provided."

    netCDF_json = process_netcdf_file(args.input[0], args.csv, args.csv or args.csv_2d, args.format)
    if args.out_file is None:
        print(json.dumps(netCDF_json, cls=NumpyEncoder, indent=4))
    else:
        file = open(args.out_file, "w")
        file.write(json.dumps(netCDF_json, cls=NumpyEncoder, indent=4))
        file.close()
except AssertionError as e:
    print('Assertion failed:', e)
except TypeError as e:
    print('Unexpected type error:', e)
