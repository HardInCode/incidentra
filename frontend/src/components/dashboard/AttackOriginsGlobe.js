import React, { useEffect, useMemo, useRef, useState } from 'react';
import Globe from 'react-globe.gl';
import { Box, Typography, LinearProgress, useTheme } from '@mui/material';
import { Public } from '@mui/icons-material';
import { brandCyan } from '../../theme';
import { getCountryCentroid } from '../../data/countryCentroids';
import { getFlagEmoji } from '../../utils/country';
import { useLanguage } from '../../context/LanguageContext';

const GLOBE_TEXTURE = {
  night: 'https://unpkg.com/three-globe/example/img/earth-night.jpg',
  day: 'https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg',
};

function buildPoints(countries) {
  if (!countries?.length) return [];
  const max = Math.max(...countries.map((c) => c.count), 1);
  return countries
    .map(({ code, count }) => {
      const geo = getCountryCentroid(code);
      if (!geo) return null;
      const ratio = count / max;
      return {
        lat: geo.lat,
        lng: geo.lng,
        size: 0.12 + ratio * 0.55,
        color: brandCyan.main,
        code: code.toUpperCase(),
        count,
        name: geo.name,
      };
    })
    .filter(Boolean);
}

export default function AttackOriginsGlobe({ countries = [], geoEnriched7d = 0, last7d = 0 }) {
  const { t } = useLanguage();
  const theme = useTheme();
  const globeRef = useRef();
  const containerRef = useRef();
  const [globeWidth, setGlobeWidth] = useState(600);
  const points = useMemo(() => buildPoints(countries), [countries]);
  const hasData = points.length > 0;
  const isDark = theme.palette.mode === 'dark';
  const globeTexture = isDark ? GLOBE_TEXTURE.night : GLOBE_TEXTURE.day;

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const update = () => {
      if (containerRef.current) setGlobeWidth(containerRef.current.clientWidth || 600);
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [hasData]);

  useEffect(() => {
    if (!globeRef.current || !hasData) return;
    const controls = globeRef.current.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.55;
    controls.enableZoom = true;
    globeRef.current.pointOfView({ lat: 18, lng: 95, altitude: 2.1 }, 0);
  }, [hasData]);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Public sx={{ color: 'primary.main', fontSize: 22 }} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6">{t('dashboard.attackOrigins')}</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            {t('dashboard.attackOriginsHint')}
          </Typography>
        </Box>
      </Box>

      {!hasData ? (
        <Box sx={{
          height: 280,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 1.5,
          px: 3,
          borderRadius: 2,
          bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.25)' : 'rgba(0,0,0,0.03)',
          border: `1px dashed ${theme.palette.divider}`,
        }}
        >
          <Public sx={{ fontSize: 48, color: 'text.disabled', opacity: 0.4 }} />
          <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', maxWidth: 420 }}>
            {t('dashboard.attackOriginsEmpty')}
          </Typography>
          {last7d > 0 && geoEnriched7d === 0 && (
            <Typography variant="caption" sx={{ color: 'warning.main', textAlign: 'center' }}>
              {t('dashboard.attackOriginsNoGeo', { count: last7d })}
            </Typography>
          )}
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 2 }}>
          <Box
            ref={containerRef}
            sx={{
              flex: 1,
              minWidth: 0,
              height: { xs: 260, md: 300 },
              borderRadius: 2,
              overflow: 'hidden',
              bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.35)' : 'rgba(10,14,26,0.92)',
            }}
          >
            <Globe
              ref={globeRef}
              width={globeWidth}
              height={280}
              globeImageUrl={globeTexture}
              backgroundColor="rgba(0,0,0,0)"
              atmosphereColor={brandCyan.main}
              atmosphereAltitude={0.12}
              pointsData={points}
              pointLat="lat"
              pointLng="lng"
              pointRadius="size"
              pointColor="color"
              pointAltitude={0.02}
              pointLabel={(d) => `<div style="padding:4px 8px;font-family:Inter,sans-serif;font-size:12px;">
                <b>${d.name}</b> (${d.code})<br/>${d.count} incident${d.count > 1 ? 's' : ''}
              </div>`}
            />
          </Box>

          <Box sx={{ width: { xs: '100%', md: 220 }, flexShrink: 0 }}>
            <Typography variant="caption" sx={{
              color: 'text.secondary',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontWeight: 700,
              mb: 1,
              display: 'block',
            }}
            >
              {t('dashboard.topCountries')}
            </Typography>
            {countries.slice(0, 8).map((item) => {
              const geo = getCountryCentroid(item.code);
              const max = countries[0]?.count || 1;
              return (
                <Box key={item.code} sx={{ mb: 1.25 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.4 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {getFlagEmoji(item.code)} {geo?.name || item.code}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {item.count}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(100, (item.count / max) * 100)}
                    sx={{
                      height: 4,
                      borderRadius: 2,
                      bgcolor: `${brandCyan.main}22`,
                      '& .MuiLinearProgress-bar': { bgcolor: brandCyan.main },
                    }}
                  />
                </Box>
              );
            })}
          </Box>
        </Box>
      )}
    </Box>
  );
}
