import {Fragment} from 'react';
import {useTheme} from '@emotion/react';

import type {SVGIconProps} from './svgIcon';
import {SvgIcon} from './svgIcon';

function IconGrid(props: SVGIconProps) {
  const theme = useTheme();
  return (
    <SvgIcon {...props} kind={theme.isChonk ? 'stroke' : 'path'}>
      {theme.isChonk ? (
        <Fragment>
          <rect x="2.75" y="2.75" width="4" height="4" rx="1" ry="1" />
          <rect x="9.25" y="2.75" width="4" height="4" rx="1" ry="1" />
          <rect x="2.75" y="9.25" width="4" height="4" rx="1" ry="1" />
          <rect x="9.25" y="9.25" width="4" height="4" rx="1" ry="1" />
        </Fragment>
      ) : (
        <Fragment>
          <path d="M5.67,7.2H1.47C.64,7.2-.03,6.52-.03,5.7V1.49C-.03.66.64,0,1.47,0h4.2c.83,0,1.5.67,1.5,1.5v4.2c0,.83-.67,1.5-1.5,1.5ZM1.47,1.49v4.2h4.21V1.49H1.47Z" />
          <path d="M5.67,16.02H1.47c-.83,0-1.5-.67-1.5-1.5v-4.2c0-.83.67-1.5,1.5-1.5h4.2c.83,0,1.5.67,1.5,1.5v4.2c0,.83-.67,1.5-1.5,1.5ZM1.47,10.31v4.2h4.2v-4.2s-4.2,0-4.2,0Z" />
          <path d="M14.51,7.2h-4.21c-.83,0-1.5-.67-1.5-1.5V1.49C8.8.66,9.47,0,10.3,0h4.21c.83,0,1.5.67,1.5,1.5v4.2c0,.83-.67,1.5-1.5,1.5ZM10.3,1.49v4.2h4.21V1.49h-4.21Z" />
          <path d="M14.51,16.02h-4.21c-.83,0-1.5-.67-1.5-1.5v-4.2c0-.83.67-1.5,1.5-1.5h4.21c.83,0,1.5.67,1.5,1.5v4.2c0,.83-.67,1.5-1.5,1.5ZM10.3,10.31v4.2h4.2v-4.2s-4.2,0-4.2,0Z" />
        </Fragment>
      )}
    </SvgIcon>
  );
}

IconGrid.displayName = 'IconGrid';

export {IconGrid};
