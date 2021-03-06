import string
from random import choice

def read_words_from(file):
  lines = open(file).read().strip().split('\n')
  return [tuple(line.split(',')) for line in lines]

def strip_punctuation(s):
  return s.translate(string.maketrans("",""), string.punctuation)


class Sparsity_Exception(Exception):
  pass


class Association_Runner(object):

  def __init__(self, builder, nupic, max_terms, min_sparsity, prediction_start, verbosity=0):
    self.builder = builder
    self.nupic = nupic
    self.max_terms = max_terms
    self.min_sparsity = min_sparsity
    self.prediction_start = prediction_start
    self.verbosity = verbosity


  def associate(self, pairs):
    print 'Prediction output for %i pairs of terms' % len(pairs)
    print '\n#%5s%16s%16s |%20s' % ('COUNT', 'TERM ONE', 'TERM TWO', 'TERM TWO PREDICTION')
    print '--------------------------------------------------------------------'

    for count in range(0, self.max_terms):
      # Loops over association list until max_terms is met
      if count >= len(pairs):
        pairs += pairs
      term1 = strip_punctuation(pairs[count][0]).lower()
      term2 = strip_punctuation(pairs[count][1]).lower()
      fetch_result = (count >= self.prediction_start)
      try:
        term2_prediction = self._feed_term(term1, fetch_result)
        self._feed_term(term2)
        self.nupic.reset()
      except Sparsity_Exception as sparsity_err:
        if self.verbosity > 0:
          print sparsity_err
          print 'skipping pair [%s, %s]' % pairs[count]
        continue
      if term2_prediction:
        print '#%5i%16s%16s |%20s' % (count, term1, term2, term2_prediction)
    
    return term2_prediction


  def direct_association(self, input_file):
    associations = read_words_from(input_file)
    self.associate(associations)


  def random_dual_association(self, term1_file, term2_file):
    all_first_terms = open(term1_file).read().strip().split('\n')
    all_second_terms = open(term2_file).read().strip().split('\n')
    associations = []
    for count in range(0, self.max_terms):
      associations.append((choice(all_first_terms), choice(all_second_terms)))
    self.associate(associations)


  def _feed_term(self, term, fetch_word_from_sdr=False):
    raw_sdr = self.builder.term_to_sdr(term)
    sparsity = raw_sdr['sparsity']
    if sparsity < self.min_sparsity:
      raise Sparsity_Exception('"%s" has a sparsity of %.1f%%, which is below the \
minimum sparsity threshold of %.1f%%.' % (term, sparsity, self.min_sparsity))
    sdr_array = self.builder.convert_bitmap_to_sdr(raw_sdr)
    predicted_bitmap = self.nupic.feed(sdr_array)
    output_sparsity = float(len(predicted_bitmap)) / (float(raw_sdr['width']) * float(raw_sdr['height'])) * 100.0
    # print 'Sparsity %s:prediction ==> %.2f%%: %.2f%%' % (term, raw_sdr['sparsity'], output_sparsity)
    if fetch_word_from_sdr:
      if len(predicted_bitmap) is 0:
        predicted_word = ' '
      else:
        predicted_word = self.builder.closest_term(predicted_bitmap)
      return predicted_word
    else:
      return None
