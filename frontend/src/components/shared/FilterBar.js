import React, { useState } from 'react';
import {
  Box, Card, CardContent, TextField, Select, MenuItem, FormControl,
  InputLabel, Button, ToggleButtonGroup, ToggleButton, InputAdornment,
  Collapse, useMediaQuery, useTheme, Chip,
} from '@mui/material';
import {
  Search, ArrowUpward, ArrowDownward, FilterList, ExpandMore, ExpandLess,
} from '@mui/icons-material';
import { iconSize } from '../../theme';
import { useLanguage } from '../../context/LanguageContext';

export default function FilterBar({
  filters = [],
  values = {},
  onChange,
  sortOptions = [],
  sortBy,
  sortDir = 'desc',
  onSortBy,
  onSortDir,
  searchValue = '',
  searchPlaceholder = 'Search...',
  onSearch,
  onClear,
  hasActiveFilters = false,
  extra,
  activeChips = [],
}) {
  const theme = useTheme();
  const { t } = useLanguage();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [filtersOpen, setFiltersOpen] = useState(!isMobile);
  const borderColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.12)';

  const filterControls = (
    <>
      {filters.map((filter) => (
        <FormControl key={filter.key} size="small" sx={{ minWidth: filter.minWidth || 130, flexShrink: 0 }}>
          <InputLabel>{filter.label}</InputLabel>
          <Select
            value={values[filter.key] || ''}
            label={filter.label}
            onChange={(e) => onChange(filter.key, e.target.value)}
          >
            <MenuItem value="">{t('common.all')}</MenuItem>
            {filter.options.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
      ))}
      {extra}
      {sortOptions.length > 0 && onSortBy && (
        <FormControl size="small" sx={{ minWidth: 150, flexShrink: 0 }}>
          <InputLabel>{t('common.sortBy')}</InputLabel>
          <Select value={sortBy || ''} label={t('common.sortBy')} onChange={(e) => onSortBy(e.target.value)}>
            {sortOptions.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      {onSortDir && (
        <ToggleButtonGroup
          value={sortDir}
          exclusive
          onChange={(e, val) => { if (val) onSortDir(val); }}
          size="small"
          sx={{
            flexShrink: 0,
            '& .MuiToggleButton-root': {
              color: 'text.secondary',
              borderColor,
              px: 1.5,
              py: 0.5,
              '&.Mui-selected': {
                color: 'primary.main',
                bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,212,170,0.1)' : 'rgba(0,168,132,0.12)',
                borderColor: theme.palette.mode === 'dark' ? 'rgba(0,212,170,0.3)' : 'rgba(0,168,132,0.35)',
              },
            },
          }}
        >
          <ToggleButton value="asc"><ArrowUpward sx={{ fontSize: iconSize.dense }} /></ToggleButton>
          <ToggleButton value="desc"><ArrowDownward sx={{ fontSize: iconSize.dense }} /></ToggleButton>
        </ToggleButtonGroup>
      )}
    </>
  );

  const showChipRow = activeChips.length > 0 || (hasActiveFilters && onClear);
  const chipRow = showChipRow && (
    <Box
      sx={{
        display: 'flex',
        gap: 1,
        flexWrap: 'wrap',
        alignItems: 'center',
        mt: 1,
        pt: 1,
        borderTop: `1px solid ${borderColor}`,
      }}
    >
      {activeChips.map((chip) => (
        <Chip
          key={chip.key}
          label={chip.label}
          size="small"
          onDelete={chip.onDelete}
          sx={{ fontSize: '0.72rem' }}
        />
      ))}
      {hasActiveFilters && onClear && (
        <Button
          size="small"
          onClick={onClear}
          sx={{ color: 'text.secondary', fontSize: '0.75rem', minWidth: 'auto', py: 0.25 }}
        >
          {t('common.clearAll')}
        </Button>
      )}
    </Box>
  );

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent sx={{ py: 1.5, pb: activeChips.length ? '8px !important' : '12px !important' }}>
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
          {onSearch && (
            <TextField
              size="small"
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(e) => onSearch(e.target.value)}
              sx={{ minWidth: { xs: '100%', sm: 200 }, flex: { xs: '1 1 100%', sm: '0 0 auto' }, flexShrink: 0 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search sx={{ color: 'text.secondary', fontSize: iconSize.inline }} />
                  </InputAdornment>
                ),
              }}
            />
          )}
          {isMobile && (
            <Button
              size="small"
              startIcon={<FilterList sx={{ fontSize: iconSize.inline }} />}
              endIcon={filtersOpen ? <ExpandLess /> : <ExpandMore />}
              onClick={() => setFiltersOpen((o) => !o)}
              sx={{ ml: 'auto' }}
            >
              {t('common.filters')}
            </Button>
          )}
          {!isMobile && filterControls}
        </Box>
        {isMobile && (
          <Collapse in={filtersOpen}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'center', mt: 1.5 }}>
              {filterControls}
            </Box>
          </Collapse>
        )}
        {chipRow}
      </CardContent>
    </Card>
  );
}
