# litex-data-cpu-lm32

Non-Python data files required to use the  with
[LiteX](https://github.com/enjoy-digital/litex.git).

The data files can be found under the Python module `litex.cpu.lm32`. The
`litex.cpu.lm32.location` value can be used to find the files on the file system.
For example;

```python
import litex.cpu.lm32

my_data_file = "abc.txt"

with open(os.path.join(litex.cpu.lm32.location, my_data_file)) as f:
    print(f.read())
```

The data files come from https://github.com/m-labs/lm32.git
and are imported using `git subtrees` to the directory
[litex/cpu/lm32/verilog](litex/cpu/lm32/verilog].

## Installing

## Manually

You can install the package manually, however this is **not** recommended.

```
git clone https://github.com/litex-hub/litex-data-cpu-lm32.git
cd litex-data-cpu-lm32
sudo python setup.py install
```

## Using [pip](https://pip.pypa.io/)

You can use [pip](https://pip.pypa.io/) to install the data package directly
from github using;

```
pip install --user git+https://github.com/litex-hub/litex-data-cpu-lm32.git
```

If you want to install for the whole system rather than just the current user,
you need to remove the `--user` argument and run as sudo like so;

```
sudo pip install git+https://github.com/litex-hub/litex-data-cpu-lm32.git
```

You can install a specific revision of the repository using;
```
pip install --user git+https://github.com/litex-hub/litex-data-cpu-lm32.git@<tag>
pip install --user git+https://github.com/litex-hub/litex-data-cpu-lm32.git@<branch>
pip install --user git+https://github.com/litex-hub/litex-data-cpu-lm32.git@<hash>
```

### With `requirements.txt` file

Add to your Python `requirements.txt` file using;
```
-e git+https://github.com/litex-hub/litex-data-cpu-lm32.git
```

To use a specific revision of the repository, use the following;
```
-e https://github.com/litex-hub/litex-data-vexriscv.git@2927346f4c513a217ac8ad076e494dd1adbf70e1
```
