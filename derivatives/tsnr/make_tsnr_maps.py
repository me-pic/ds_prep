# -*- coding: utf-8 -*-
import logging
from pathlib import Path

import bids
import click
from nipype.algorithms.confounds import TSNR


@click.command()
@click.argument('ds_name', type=str)
@click.argument('ds_path', type=click.Path())
@click.argument('output_filepath', type=click.Path())
@click.option('--echo', type=str, default=None, help='Specify the echo value to compute tSNR maps from fMRIPrep outputs')
@click.option('--tedana', is_flag=True, help='Flag to specify if working with tedana outputs. If specified, will compute tSNR maps for optcom and denoised images')
@click.option('--subject', type=str, default=None, help='Specify the subject id on which to compute the tSNR maps')
def main(ds_name, ds_path, output_filepath, echo, tedana, subject):
    tsnr_maps(ds_name, str(Path(ds_path)), str(Path(output_filepath)), echo, tedana, subject)

def tsnr_maps(ds_name, ds_path, output_filepath, echo=None, tedana=False, subject=None):
    logger = logging.getLogger(__name__)
    logger.info(f'generating tsnr maps from {Path(ds_path).name.split('.')[-1]} data for the {ds_name} dataset')
    logger.info(f"loading BIDS: {ds_name}")

    layout = bids.BIDSLayout(ds_path, validate=False, is_derivative=True)

    if subject is None:
        subject = bids.layout.Query.ANY

    if tedana:
        # Get optimally combined and denoised images
        bolds_optcom = layout.get(subject=subject, suffix='bold', extension='.nii.gz', desc='optcom')
        bolds_denoised = layout.get(subject=subject, suffix='bold', extension='.nii.gz', desc='denoised')
        bolds = [*bolds_optcom, *bolds_denoised]
    else:
        bolds = layout.get(subject=subject, suffix='bold', extension='.nii.gz', desc='preproc', echo=echo)

    for bold in bolds:
        entities = bold.get_entities()
        entities.update({
            'stat': 'tsnr',
            'suffix': 'statmap'
        })
        if echo is not None:
            entities.update({
                'echo': echo
            })

        pattern="sub-{subject}[/ses-{session}]/{datatype}/sub-{subject}[_ses-{session}]_task-{task}_run-{run}[_echo-{echo}][_space-{space}]_stat-{stat}_desc-{desc}_{suffix}.nii.gz"
        tsnr_path = layout.build_path(entities, pattern, validate=False).replace(ds_path, output_filepath)

        Path(tsnr_path).parent.mkdir(parents=True, exist_ok=True)
        if not Path(tsnr_path).exists():
            try:
                logger.info(f'Computing tSNR maps for: {bold.filename}')
                tsnr_if = TSNR(
                    in_file=bold.path,
                    tsnr_file=tsnr_path,
                    stddev_file=tsnr_path.replace('stat-tsnr', 'stat-stdev'),
                    mean_file=tsnr_path.replace('stat-tsnr', 'stat-mean'),
                )
                tsnr_if.run()
                del tsnr_if
            except:
                logger.info(f"could not process {bold.filename}")

    
if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()